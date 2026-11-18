"""旧阶段测试使用隔离的测试身份；认证专项测试走真实会话检查。"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.core import request_auth
from app.core.user_scope import bind_user, reset_user
from app.services.auth_repository import Principal


def pytest_addoption(parser):
    parser.addoption("--run-browser-e2e", action="store_true", default=False,
                     help="运行独立 SQLite 与真实浏览器的端到端测试")
    parser.addoption("--run-mysql-integration", action="store_true", default=False,
                     help="使用 MYSQL_TEST_ADMIN_URL 创建并清理独立 MySQL 测试库")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("browser_e2e") and not config.getoption("--run-browser-e2e"):
            item.add_marker(pytest.mark.skip(reason="需显式传入 --run-browser-e2e"))
        if item.get_closest_marker("mysql_integration") and not config.getoption(
            "--run-mysql-integration"
        ):
            item.add_marker(pytest.mark.skip(reason="需显式传入 --run-mysql-integration"))


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


@pytest.fixture
def mysql_test_engine():
    """每例独占随机 MySQL 库；仅连接显式提供的测试管理端。"""
    raw_url = os.environ.get("MYSQL_TEST_ADMIN_URL")
    if not raw_url:
        pytest.fail("必须设置 MYSQL_TEST_ADMIN_URL；只接受独立测试服务器的管理连接。")
    admin_url = make_url(raw_url)
    if admin_url.drivername != "mysql+pymysql" or admin_url.database != "mysql":
        pytest.fail("MYSQL_TEST_ADMIN_URL 必须指向 mysql 系统库，不能指向业务库。")

    test_database = f"job_agent_test_{uuid4().hex}"
    admin_engine = create_engine(admin_url, pool_pre_ping=True)
    created = False
    try:
        with admin_engine.begin() as connection:
            connection.exec_driver_sql(
                f"CREATE DATABASE `{test_database}` CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_unicode_ci"
            )
        created = True
        engine = create_engine(admin_url.set(database=test_database), pool_pre_ping=True)
        try:
            yield engine
        finally:
            engine.dispose()
    finally:
        if created:
            with admin_engine.begin() as connection:
                connection.exec_driver_sql(f"DROP DATABASE `{test_database}`")
        admin_engine.dispose()
