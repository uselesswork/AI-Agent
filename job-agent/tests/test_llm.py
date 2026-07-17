import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.config import ProviderConfig
from app.services.llm import OpenAICompatibleClient


def response_with(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_openai_client_uses_openai_output_token_parameter() -> None:
    config = ProviderConfig(
        provider="openai",
        api_key="sk-test",
        model="gpt-test",
        base_url="https://api.openai.com/v1",
        timeout_seconds=30,
        max_retries=0,
        max_output_tokens=1024,
    )
    client = OpenAICompatibleClient(config)
    create = AsyncMock(return_value=response_with('{"ok":true}'))
    client.client.chat.completions.create = create

    result = asyncio.run(client.generate_json("输出 JSON", "测试"))

    assert result == {"ok": True}
    kwargs = create.await_args.kwargs
    assert kwargs["max_completion_tokens"] == 1024
    assert "max_tokens" not in kwargs


def test_deepseek_client_disables_thinking_for_json_extraction() -> None:
    config = ProviderConfig(
        provider="deepseek",
        api_key="ds-test",
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        timeout_seconds=30,
        max_retries=0,
        max_output_tokens=2048,
    )
    client = OpenAICompatibleClient(config)
    create = AsyncMock(return_value=response_with('{"ok":true}'))
    client.client.chat.completions.create = create

    result = asyncio.run(client.generate_json("输出 JSON", "测试"))

    assert result == {"ok": True}
    kwargs = create.await_args.kwargs
    assert kwargs["max_tokens"] == 2048
    assert kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
