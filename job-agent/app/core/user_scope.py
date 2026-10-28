"""请求内账号归属；未绑定账号时持久化操作应拒绝。"""

from contextvars import ContextVar, Token

_current_user: ContextVar[int | None] = ContextVar("job_agent_user_id", default=None)


def bind_user(user_id: int) -> Token:
    return _current_user.set(user_id)


def reset_user(token: Token) -> None:
    _current_user.reset(token)


def current_user_id() -> int:
    user_id = _current_user.get()
    if user_id is None:
        raise RuntimeError("缺少已认证的用户上下文。")
    return user_id
