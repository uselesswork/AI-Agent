"""将仅含规则结果的本地报告导入 Hub；原文和模型输出不进入报告。"""

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def save_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")


def upload_report(path: Path, hub_url: str) -> str:
    body = path.read_bytes()
    request = Request(f"{hub_url.rstrip('/')}/api/imports/job-agent", data=body,
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=10) as response:
            if response.status not in (200, 201):
                raise RuntimeError(f"Hub 报告导入返回 HTTP {response.status}")
            result = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Hub 报告导入返回 HTTP {exc.code}；本地报告保留可重试。") from exc
    return result["runId"]
