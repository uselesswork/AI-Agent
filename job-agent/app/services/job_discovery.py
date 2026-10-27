"""只读取用户指定的 Greenhouse/Lever 公开职位接口；不抓取任意 URL。"""

import json
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.models.discovery import DiscoverySearch, SourceName

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_LEVER_PAGES = 3
LEVER_PAGE_SIZE = 100


class DiscoveryServiceError(RuntimeError):
    """公开职位接口不可用或返回无效数据。"""


class PostingNotFoundError(LookupError):
    """指定职位已不存在。"""


@dataclass(frozen=True)
class Posting:
    source: SourceName
    board_token: str
    external_id: str
    title: str
    company: str | None
    location: str | None
    commitment: str | None
    job_url: str
    description: str


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"p", "li", "br", "div", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1
        elif tag in {"p", "li", "div", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _plain_text(value: str | None) -> str:
    parser = _PlainText()
    parser.feed(unescape(unescape(value or "")))
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def fetch_json(url: str):
    """请求地址只由本模块固定域名与已校验的标识拼成，不接受任意 URL。"""
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "job-agent/0.1"})
    try:
        with build_opener(_NoRedirect).open(request, timeout=10) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 404:
            raise PostingNotFoundError("该职位或招聘板不存在。") from exc
        raise DiscoveryServiceError(f"职位来源返回 HTTP {exc.code}。") from exc
    except (URLError, TimeoutError) as exc:
        raise DiscoveryServiceError("无法连接职位来源，请稍后重试。") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise DiscoveryServiceError("职位来源返回内容过大，请缩小查询范围。")
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DiscoveryServiceError("职位来源没有返回有效 JSON。") from exc


def _url(source: SourceName, board: str, posting_id: str | None = None) -> str:
    if source == "greenhouse":
        base = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
        return f"{base}/{posting_id}?content=true" if posting_id else f"{base}?content=true"
    base = f"https://api.lever.co/v0/postings/{board}"
    return f"{base}/{posting_id}?mode=json" if posting_id else base


def _as_posting(source: SourceName, board: str, raw: dict) -> Posting | None:
    if not isinstance(raw, dict):
        return None
    posting_id = str(raw.get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", posting_id):
        return None
    if source == "greenhouse":
        title = str(raw.get("title") or "").strip()
        location = raw.get("location") or {}
        location = location.get("name") if isinstance(location, dict) else None
        company = raw.get("company_name")
        description = _plain_text(raw.get("content"))
        url = raw.get("absolute_url") or f"https://boards.greenhouse.io/{board}/jobs/{posting_id}"
        commitment = None
    else:
        title = str(raw.get("text") or "").strip()
        categories = raw.get("categories") or {}
        location = categories.get("location") if isinstance(categories, dict) else None
        commitment = categories.get("commitment") if isinstance(categories, dict) else None
        company = None
        parts = [raw.get("descriptionPlain") or raw.get("openingPlain") or ""]
        for item in raw.get("lists") or []:
            if isinstance(item, dict):
                parts.append(item.get("text") or "")
                parts.append(_plain_text(item.get("content")))
        parts.append(raw.get("additionalPlain") or "")
        description = "\n".join(part.strip() for part in parts if isinstance(part, str) and part.strip())
        url = raw.get("hostedUrl") or f"https://jobs.lever.co/{board}/{posting_id}"
    if not title or not isinstance(url, str) or not url.startswith(("https://", "http://")):
        return None
    return Posting(source=source, board_token=board, external_id=posting_id,
                   title=title, company=str(company) if company else None,
                   location=str(location) if location else None,
                   commitment=str(commitment) if commitment else None,
                   job_url=url, description=description[:30000])


def list_postings(source: SourceName, board: str) -> tuple[list[Posting], bool]:
    if source == "greenhouse":
        response = fetch_json(_url(source, board))
        if not isinstance(response, dict) or not isinstance(response.get("jobs"), list):
            raise DiscoveryServiceError("Greenhouse 职位列表格式不正确。")
        raw_jobs = response["jobs"]
        truncated = False
    else:
        raw_jobs = []
        truncated = False
        for page in range(MAX_LEVER_PAGES):
            response = fetch_json(f"{_url(source, board)}?mode=json&skip={page * LEVER_PAGE_SIZE}"
                                  f"&limit={LEVER_PAGE_SIZE}")
            if not isinstance(response, list):
                raise DiscoveryServiceError("Lever 职位列表格式不正确。")
            raw_jobs.extend(response)
            if len(response) < LEVER_PAGE_SIZE:
                break
            if page == MAX_LEVER_PAGES - 1:
                truncated = True
    postings = [_as_posting(source, board, item) for item in raw_jobs]
    return [item for item in postings if item is not None], truncated


def get_posting(source: SourceName, board: str, posting_id: str) -> Posting:
    response = fetch_json(_url(source, board, posting_id))
    posting = _as_posting(source, board, response)
    if posting is None or posting.external_id != posting_id:
        raise PostingNotFoundError("该职位已不存在或返回数据不完整。")
    return posting


def filter_postings(postings: list[Posting], query: DiscoverySearch) -> list[Posting]:
    keyword = query.keyword.strip().casefold()
    location = query.location.strip().casefold()
    internship_words = ("intern", "实习", "co-op", "coop")
    return [item for item in postings if (
        (not keyword or keyword in f"{item.title} {item.description}".casefold())
        and (not location or location in (item.location or "").casefold())
        and (not query.internship_only or any(word in
             f"{item.title} {item.commitment or ''}".casefold() for word in internship_words))
    )]
