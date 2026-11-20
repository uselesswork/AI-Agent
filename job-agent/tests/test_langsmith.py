import asyncio
from contextlib import nullcontext

import pytest

from app.core.config import LLMConfigurationError, Settings
from app.observability import langsmith


class FakeTrace:
    def __init__(self, inputs: dict[str, str]) -> None:
        self.inputs = inputs
        self.outputs: dict | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def end(self, *, outputs: dict) -> None:
        self.outputs = outputs


def enabled_settings() -> Settings:
    return Settings(
        _env_file=None,
        langsmith_tracing=True,
        langsmith_api_key="test-key",
        langsmith_project="job-agent-test",
    )


def test_trace_contains_only_call_summary(monkeypatch) -> None:
    traces = []

    def fake_trace(*args, **kwargs):
        run = FakeTrace(kwargs["inputs"])
        traces.append(run)
        return run

    monkeypatch.setattr(langsmith, "tracing_context", lambda **kwargs: nullcontext())
    monkeypatch.setattr(langsmith, "trace", fake_trace)
    monkeypatch.setattr(langsmith, "Client", lambda **kwargs: object())
    tracer = langsmith.LangSmithTracer(enabled_settings())

    async def operation():
        return {"resume": "敏感简历正文"}, {"prompt_tokens": 12, "total_tokens": 15}

    result = asyncio.run(tracer.run("openai", "gpt-test", operation))

    assert result == {"resume": "敏感简历正文"}
    assert traces[0].inputs == {"provider": "openai", "model": "gpt-test"}
    assert traces[0].outputs == {
        "status": "ok",
        "prompt_tokens": 12,
        "total_tokens": 15,
    }


def test_model_failure_is_sanitized_and_not_retried(monkeypatch) -> None:
    traces = []
    calls = 0

    def fake_trace(*args, **kwargs):
        run = FakeTrace(kwargs["inputs"])
        traces.append(run)
        return run

    monkeypatch.setattr(langsmith, "tracing_context", lambda **kwargs: nullcontext())
    monkeypatch.setattr(langsmith, "trace", fake_trace)
    monkeypatch.setattr(langsmith, "Client", lambda **kwargs: object())
    tracer = langsmith.LangSmithTracer(enabled_settings())

    async def operation():
        nonlocal calls
        calls += 1
        raise ValueError("包含敏感正文的异常")

    with pytest.raises(ValueError, match="包含敏感正文的异常"):
        asyncio.run(tracer.run("deepseek", "test-model", operation))

    assert calls == 1
    assert traces[0].outputs == {"status": "error", "error_type": "ValueError"}


def test_tracing_failure_does_not_repeat_model_call(monkeypatch) -> None:
    calls = 0

    def broken_trace(*args, **kwargs):
        raise RuntimeError("追踪服务不可用")

    monkeypatch.setattr(langsmith, "tracing_context", lambda **kwargs: nullcontext())
    monkeypatch.setattr(langsmith, "trace", broken_trace)
    monkeypatch.setattr(langsmith, "Client", lambda **kwargs: object())
    tracer = langsmith.LangSmithTracer(enabled_settings())

    async def operation():
        nonlocal calls
        calls += 1
        return {"ok": True}, {}

    assert asyncio.run(tracer.run("openai", "gpt-test", operation)) == {"ok": True}
    assert calls == 1


def test_tracing_requires_key_when_enabled() -> None:
    with pytest.raises(LLMConfigurationError, match="LANGSMITH_API_KEY"):
        langsmith.LangSmithTracer(
            Settings(_env_file=None, langsmith_tracing=True, langsmith_api_key=None)
        )
