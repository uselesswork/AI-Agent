"""独立 MySQL 测试库中的登录、投递事务和账号隔离。"""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url

from app.api import applications
from app.core.database_schema import application_events, applications_table, metadata, user_assets
from app.main import app
from app.services import application_repository
from app.services.application_repository import ApplicationRepository
from app.services.auth_repository import AuthRepository
from tests.test_applications_api import application_payload

PASSWORD_A = "MySQLTestPassword-A1"
PASSWORD_B = "MySQLTestPassword-B2"


@pytest.fixture
def mysql_repository():
    raw_url = os.environ.get("MYSQL_TEST_ADMIN_URL")
    if not raw_url:
        pytest.fail("必须设置 MYSQL_TEST_ADMIN_URL；只接受独立测试服务器的管理连接。")
    admin_url = make_url(raw_url)
    if admin_url.drivername != "mysql+pymysql" or admin_url.database != "mysql":
        pytest.fail("MYSQL_TEST_ADMIN_URL 必须指向 mysql 系统库，不能指向业务库。")

    test_database = f"job_agent_test_{uuid4().hex}"
    admin_engine = create_engine(admin_url, pool_pre_ping=True)
    repository = None
    created = False
    try:
        with admin_engine.begin() as connection:
            connection.exec_driver_sql(
                f"CREATE DATABASE `{test_database}` CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_unicode_ci"
            )
        created = True
        test_url = admin_url.set(database=test_database)
        repository = ApplicationRepository(test_url.render_as_string(hide_password=False))
        metadata.create_all(repository.engine)
        yield repository
    finally:
        if repository is not None:
            repository.engine.dispose()
        if created:
            with admin_engine.begin() as connection:
                connection.exec_driver_sql(f"DROP DATABASE `{test_database}`")
        admin_engine.dispose()


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["csrf_token"]


@pytest.mark.mysql_integration
@pytest.mark.auth_real
def test_mysql_login_isolation_transactions_and_cascade(monkeypatch, mysql_repository) -> None:
    repository = mysql_repository
    monkeypatch.setattr(applications, "get_repository", lambda: repository)
    accounts = AuthRepository(repository.engine)
    first_id = accounts.create_user("mysql_owner_a", PASSWORD_A)
    accounts.create_user("mysql_owner_b", PASSWORD_B)

    with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as first, \
            TestClient(app, base_url="http://localhost") as second:
        assert first.get("/ready").status_code == 200
        assert first.get("/api/applications").status_code == 401
        csrf_a = _login(first, "mysql_owner_a", PASSWORD_A)
        csrf_b = _login(second, "mysql_owner_b", PASSWORD_B)
        payload = application_payload()
        assert first.post("/api/applications", json=payload).status_code == 403
        created = first.post("/api/applications", json=payload,
                             headers={"X-CSRF-Token": csrf_a})
        assert created.status_code == 201
        record_id = created.json()["id"]
        assert second.get("/api/applications").json() == []
        assert second.get(f"/api/applications/{record_id}").status_code == 404
        assert second.patch(f"/api/applications/{record_id}", json={"status": "面试"},
                            headers={"X-CSRF-Token": csrf_b}).status_code == 404

        updated = first.patch(f"/api/applications/{record_id}", json={"status": "面试"},
                              headers={"X-CSRF-Token": csrf_a})
        assert updated.status_code == 200
        assert updated.json()["status"] == "面试"
        with repository.engine.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(application_events).where(
                application_events.c.application_id == record_id)) == 2

        def fail_event(*_args, **_kwargs):
            raise RuntimeError("模拟事务中断")

        with monkeypatch.context() as patch:
            patch.setattr(application_repository, "add_event", fail_event)
            failed = first.post("/api/applications", json=payload,
                                headers={"X-CSRF-Token": csrf_a})
            assert failed.status_code == 500
        with repository.engine.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(applications_table)) == 1

        second_created = second.post("/api/applications", json=payload,
                                     headers={"X-CSRF-Token": csrf_b})
        assert second_created.status_code == 201
        assert first.delete(f"/api/applications/{record_id}",
                            headers={"X-CSRF-Token": csrf_a}).status_code == 204
        assert first.get("/api/applications").json() == []
        assert len(second.get("/api/applications").json()) == 1
        with repository.engine.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(application_events).where(
                application_events.c.application_id == record_id)) == 0
            assert connection.scalar(select(func.count()).select_from(user_assets).where(
                user_assets.c.entity_type == "application",
                user_assets.c.entity_id == record_id,
                user_assets.c.user_id == first_id)) == 0

        assert first.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_a}).status_code == 204
        assert first.get("/api/applications").status_code == 401
