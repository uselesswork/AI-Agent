import json
from time import perf_counter
from typing import Any, Protocol
from uuid import uuid4

from openai import APIError, APITimeoutError, AsyncOpenAI

from app.core.config import ProviderConfig
from app.observability.langsmith import LangSmithTracer
from app.services.call_metadata import ModelCallMetadata, current_observer


class LLMServiceError(RuntimeError):
    """模型服务调用失败。"""


class LLMResponseError(LLMServiceError):
    """模型返回空内容或无效 JSON。"""


class JSONGenerator(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def model(self) -> str: ...

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]: ...


class OpenAICompatibleClient:
    def __init__(self, config: ProviderConfig, tracer: LangSmithTracer | None = None) -> None:
        self.config = config
        self.tracer = tracer
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
        )

    @property
    def provider(self) -> str:
        return self.config.provider

    @property
    def model(self) -> str:
        return self.config.model

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if self.tracer is None:
            result, _ = await self._generate_json(system_prompt, user_prompt)
            return result
        return await self.tracer.run(
            self.provider,
            self.model,
            lambda: self._generate_json(system_prompt, user_prompt),
        )

    async def _generate_json(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[dict[str, Any], dict[str, int]]:
        observer = current_observer()
        request_id = uuid4().hex if observer is not None else None
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        started = perf_counter()
        try:
            if self.config.provider == "deepseek":
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=self.config.max_output_tokens,
                    extra_body={"thinking": {"type": "disabled"}},
                )
            else:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_completion_tokens=self.config.max_output_tokens,
                )
        except APITimeoutError as exc:
            raise LLMServiceError("大模型请求超时，请稍后重试。") from exc
        except APIError as exc:
            raise LLMServiceError("大模型服务调用失败，请检查密钥、模型和网络配置。") from exc

        latency_ms = max(0, round((perf_counter() - started) * 1000))
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None)
        output_tokens = getattr(usage, "completion_tokens", None)
        if observer is not None:
            actual_model = getattr(response, "model", None)
            observer(ModelCallMetadata(
                request_id=request_id,
                model_id=actual_model.strip() if isinstance(actual_model, str) and actual_model.strip() else None,
                latency_ms=latency_ms,
                input_tokens=input_tokens if type(input_tokens) is int and input_tokens >= 0 else None,
                output_tokens=output_tokens if type(output_tokens) is int and output_tokens >= 0 else None,
            ))

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise LLMResponseError("大模型返回了空内容，请重试。")

        normalized = content.strip()
        if normalized.startswith("```"):
            normalized = normalized.removeprefix("```json").removeprefix("```")
            normalized = normalized.removesuffix("```").strip()
        try:
            data = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise LLMResponseError("大模型未返回合法 JSON，请重试。") from exc
        if not isinstance(data, dict):
            raise LLMResponseError("大模型返回的 JSON 顶层必须是对象。")
        token_counts = {
            key: count
            for key, count in (
                ("prompt_tokens", getattr(usage, "prompt_tokens", None)),
                ("completion_tokens", getattr(usage, "completion_tokens", None)),
                ("total_tokens", getattr(usage, "total_tokens", None)),
            )
            if isinstance(count, int)
        }
        return data, token_counts
