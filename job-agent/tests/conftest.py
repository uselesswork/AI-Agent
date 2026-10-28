"""旧阶段测试使用隔离的测试身份；认证专项测试走真实会话检查。"""

import pytest

from app.core import request_auth
from app.core.user_scope import bind_user, reset_user
from app.services.auth_repository import Principal


@pytest.fixture(autouse=True)
def test_identity(monkeypatch, request):
    if request.node.get_closest_marker("auth_real"):
        yield
        return
    token = bind_user(1)
    monkeypatch.setattr(request_auth, "resolve_request", lambda _request, _engine: Principal(
        user_id=1, username="test-owner", csrf_token="test-csrf", token_hash="test-token",
    ))
    try:
        yield
    finally:
        reset_user(token)
