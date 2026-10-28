"""记录最小化访问日志：不记录请求体、查询参数、Cookie 或账号。"""

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request

logger = logging.getLogger("uvicorn.error")


async def log_request(request: Request, call_next):
    request_id = uuid4().hex
    started = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        route = request.scope.get("route")
        path = getattr(route, "path", "<unmatched>")
        logger.info(
            "request_id=%s method=%s route=%s status=%s duration_ms=%.1f",
            request_id, request.method, path, status_code,
            (perf_counter() - started) * 1000,
        )
