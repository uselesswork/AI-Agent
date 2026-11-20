"""仅供显式 live 评估使用的单次模型响应摘要。"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from collections.abc import Callable, Iterator


@dataclass(frozen=True)
class ModelCallMetadata:
    request_id: str
    model_id: str | None
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None


_observer: ContextVar[Callable[[ModelCallMetadata], None] | None] = ContextVar(
    "live_model_call_observer", default=None
)


@contextmanager
def observe_model_calls(callback: Callable[[ModelCallMetadata], None]) -> Iterator[None]:
    token = _observer.set(callback)
    try:
        yield
    finally:
        _observer.reset(token)


def current_observer() -> Callable[[ModelCallMetadata], None] | None:
    return _observer.get()
