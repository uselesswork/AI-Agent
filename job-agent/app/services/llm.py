import json
from typing import Any, Protocol

from openai import APIError, APITimeoutError, AsyncOpenAI

from app.core.config import ProviderConfig


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
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
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
        return data
