"""旧阶段测试使用隔离的测试身份；认证专项测试走真实会话检查。"""

import pytest

from app.core import request_auth
from app.core.user_scope import bind_user, reset_user
from app.services.auth_repository import Principal


def pytest_addoption(parser):
    parser.addoption("--run-browser-e2e", action="store_true", default=False,
                     help="运行独立 SQLite 与真实浏览器的端到端测试")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-browser-e2e"):
        return
    skip = pytest.mark.skip(reason="浏览器端到端测试需显式传入 --run-browser-e2e")
    for item in items:
        if item.get_closest_marker("browser_e2e"):
            item.add_marker(skip)


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
