"""只上传模型调用摘要，避免将简历、岗位或模型正文发往追踪服务。"""

import logging
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Any

from langsmith import Client, trace, tracing_context

from app.core.config import LLMConfigurationError, Settings, get_settings

logger = logging.getLogger(__name__)


class LangSmithTracer:
    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.langsmith_tracing
        self.project = settings.langsmith_project.strip()
        self.client: Client | None = None
        if not self.enabled:
            return
        key = settings.langsmith_api_key
        if key is None or not key.get_secret_value().strip():
            raise LLMConfigurationError("LANGSMITH_TRACING=true 时必须配置 LANGSMITH_API_KEY。")
        if not self.project:
            raise LLMConfigurationError("LANGSMITH_PROJECT 不能为空。")
        try:
            self.client = Client(
                api_key=key.get_secret_value(),
                api_url=settings.langsmith_endpoint.rstrip("/"),
                omit_traced_runtime_info=True,
            )
        except Exception:
            logger.warning("LangSmith 客户端初始化失败，已跳过模型调用追踪。")
            self.enabled = False

    async def run(
        self,
        provider: str,
        model: str,
        operation: Callable[[], Awaitable[tuple[dict[str, Any], dict[str, int]]]],
    ) -> dict[str, Any]:
        if not self.enabled:
            result, _ = await operation()
            return result

        called = False
        result: dict[str, Any] | None = None
        failure: Exception | None = None
        try:
            with tracing_context(enabled=True, client=self.client, project_name=self.project):
                async with trace(
                    "job-agent.model-call",
                    run_type="chain",
                    inputs={"provider": provider, "model": model},
                    parent="ignore",
                ) as run:
                    try:
                        called = True
                        result, usage = await operation()
                    except Exception as exc:
                        failure = exc
                        run.end(outputs={"status": "error", "error_type": type(exc).__name__})
                    else:
                        run.end(outputs={"status": "ok", **usage})
        except Exception:
            # 追踪初始化或发送失败不能让已完成的模型请求重复执行。
            logger.warning("LangSmith 追踪不可用，本次模型调用继续正常处理。")
            if not called:
                result, _ = await operation()
        if failure is not None:
            raise failure
        assert result is not None
        return result


@lru_cache
def get_langsmith_tracer() -> LangSmithTracer:
    return LangSmithTracer(get_settings())
