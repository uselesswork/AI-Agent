"""会话 Cookie、同源与 CSRF 检查；所有非公开 API 请求均须通过。"""

import hmac
from urllib.parse import urlsplit

from fastapi import Request
from sqlalchemy.engine import Engine

from app.services.auth_repository import AuthRepository, Principal

COOKIE_NAME = "job_agent_session"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuthFailure(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def check_origin(request: Request) -> None:
    if request.method not in UNSAFE_METHODS:
        return
    source = request.headers.get("origin") or request.headers.get("referer")
    if source is None:
        return  # 非浏览器客户端仍须提交有效 CSRF 令牌。
    parsed = urlsplit(source)
    target = urlsplit(str(request.url))
    expected = (target.scheme, target.netloc.lower())
    if (parsed.scheme, parsed.netloc.lower()) != expected:
        raise AuthFailure(403, "跨来源写入请求已拒绝。")


def resolve_request(request: Request, engine: Engine) -> Principal:
    raw_token = request.cookies.get(COOKIE_NAME)
    if not raw_token:
        raise AuthFailure(401, "请先登录。")
    principal = AuthRepository(engine).session(raw_token)
    if principal is None:
        raise AuthFailure(401, "登录已失效，请重新登录。")
    if request.method in UNSAFE_METHODS:
        check_origin(request)
        submitted = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(submitted, principal.csrf_token):
            raise AuthFailure(403, "缺少或无效的防跨站令牌。")
    return principal
