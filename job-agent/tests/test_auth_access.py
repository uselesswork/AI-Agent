"""第十三阶段真实会话、CSRF、跨账号隔离与数据导出删除。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api import applications, library
from app.core.database_schema import applications_table, job_imports, user_assets
from app.core.user_scope import bind_user, reset_user
from app.main import app
from app.services.application_repository import ApplicationRepository
from app.services.auth_repository import AuthRepository
from app.services.discovery_repository import DiscoveryRepository
from app.services.library_repository import LibraryRepository
from scripts.upgrade_user_access import prepare_schema
from tests.test_applications_api import application_payload

PASSWORD_A = "StrongLocalPassphrase-A1"
PASSWORD_B = "StrongLocalPassphrase-B2"


def _setup(monkeypatch, tmp_path: Path):
    repo = ApplicationRepository(f"sqlite+pysqlite:///{(tmp_path / 'auth.db').as_posix()}")
    monkeypatch.setattr(applications, "get_repository", lambda: repo)
    monkeypatch.setattr(library, "get_library_repository", lambda: LibraryRepository(repo.engine))
    accounts = AuthRepository(repo.engine)
    first = accounts.create_user("owner_a", PASSWORD_A)
    second = accounts.create_user("owner_b", PASSWORD_B)
    return repo, first, second


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    return response.json()["csrf_token"]


@pytest.mark.auth_real
def test_login_csrf_logout_and_unauthorized(monkeypatch, tmp_path: Path) -> None:
    _setup(monkeypatch, tmp_path)
    with TestClient(app, base_url="http://localhost") as client:
        assert client.get("/api/applications").status_code == 401
        assert client.get("/api/auth/status").json() == {"configured": True}
        assert client.post("/api/auth/login", json={
            "username": "owner_a", "password": "wrong",
        }).status_code == 401
        csrf = _login(client, "owner_a", PASSWORD_A)
        assert client.get("/api/auth/me").json()["username"] == "owner_a"
        assert client.post("/api/applications", json=application_payload()).status_code == 403
        assert client.post("/api/applications", json=application_payload(), headers={
            "X-CSRF-Token": csrf, "Origin": "https://attacker.example",
        }).status_code == 403
        created = client.post("/api/applications", json=application_payload(), headers={
            "X-CSRF-Token": csrf,
        })
        assert created.status_code == 201
        assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
        assert client.get("/api/applications").status_code == 401


@pytest.mark.auth_real
def test_accounts_cannot_read_or_reuse_each_others_data(monkeypatch, tmp_path: Path) -> None:
    repo, first_id, second_id = _setup(monkeypatch, tmp_path)
    with TestClient(app, base_url="http://localhost") as first, TestClient(
        app, base_url="http://localhost",
    ) as second:
        csrf_a = _login(first, "owner_a", PASSWORD_A)
        csrf_b = _login(second, "owner_b", PASSWORD_B)
        app_a = first.post("/api/applications", json=application_payload(), headers={
            "X-CSRF-Token": csrf_a,
        }).json()["id"]
        assert second.get("/api/applications").json() == []
        assert second.get(f"/api/applications/{app_a}").status_code == 404
        assert second.get(f"/api/applications/{app_a}/draft").status_code == 404
        assert second.get(f"/api/planning/applications/{app_a}/milestones").status_code == 404
        assert second.patch(f"/api/applications/{app_a}", json={"status": "面试"}, headers={
            "X-CSRF-Token": csrf_b,
        }).status_code == 404

        resume = {"filename": "测试.txt", "profile": application_payload()["candidate_profile"]}
        one = first.post("/api/library/resumes", json=resume, headers={
            "X-CSRF-Token": csrf_a,
        }).json()["asset"]["id"]
        assert second.get("/api/library/resumes").json() == []
        assert second.get(f"/api/library/resumes/{one}").status_code == 404
        two = second.post("/api/library/resumes", json=resume, headers={
            "X-CSRF-Token": csrf_b,
        }).json()["asset"]["id"]
        assert one != two
        with repo.engine.connect() as connection:
            owners = connection.execute(select(user_assets.c.user_id).where(
                user_assets.c.entity_type == "resume",
                user_assets.c.entity_id.in_([one, two]),
            )).scalars().all()
        assert set(owners) == {first_id, second_id}


@pytest.mark.auth_real
def test_export_delete_only_current_account(monkeypatch, tmp_path: Path) -> None:
    repo, first_id, _ = _setup(monkeypatch, tmp_path)
    with TestClient(app, base_url="http://localhost") as first, TestClient(
        app, base_url="http://localhost",
    ) as second:
        csrf_a = _login(first, "owner_a", PASSWORD_A)
        csrf_b = _login(second, "owner_b", PASSWORD_B)
        first.post("/api/applications", json=application_payload(), headers={
            "X-CSRF-Token": csrf_a,
        })
        second.post("/api/applications", json=application_payload(), headers={
            "X-CSRF-Token": csrf_b,
        })
        exported = first.get("/api/auth/export")
        assert exported.status_code == 200
        assert exported.headers["cache-control"] == "no-store"
        assert len(exported.json()["data"]["applications"]) == 1
        assert "password_hash" not in exported.text and "csrf_token" not in exported.text
        assert first.post("/api/auth/delete", json={
            "password": "wrong", "confirmed": True,
        }, headers={"X-CSRF-Token": csrf_a}).status_code == 403
        deleted = first.post("/api/auth/delete", json={
            "password": PASSWORD_A, "confirmed": True,
        }, headers={"X-CSRF-Token": csrf_a})
        assert deleted.status_code == 204
        assert first.get("/api/auth/me").status_code == 401
        assert len(second.get("/api/applications").json()) == 1
    with repo.engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(user_assets).where(
            user_assets.c.user_id == first_id)) == 0
        assert connection.scalar(select(func.count()).select_from(applications_table)) == 1


def test_bootstrap_schema_rejects_sqlite(tmp_path: Path) -> None:
    repo = ApplicationRepository(f"sqlite+pysqlite:///{(tmp_path / 'schema.db').as_posix()}")
    with pytest.raises(ValueError, match="只用于 MySQL"):
        prepare_schema(repo.engine)
    repo.engine.dispose()


@pytest.mark.auth_real
def test_import_identity_is_independent_per_account(monkeypatch, tmp_path: Path) -> None:
    repo, first_id, second_id = _setup(monkeypatch, tmp_path)
    library_repo = LibraryRepository(repo.engine)
    imports = DiscoveryRepository(repo.engine)
    from app.models.library import JobAssetCreate
    from app.models.job import JobProfile

    profile = JobProfile(title="Python 实习", company="测试企业")
    tokens = []
    try:
        for user_id in (first_id, second_id):
            token = bind_user(user_id)
            tokens.append(token)
            job_id = library_repo.save_job(JobAssetCreate(profile=profile)).asset.id
            record, created = imports.create(
                "greenhouse", "sample", "same-posting", job_id,
                "https://boards.greenhouse.io/sample/jobs/same-posting",
            )
            assert created is True
            assert record.job_id == job_id
            reset_user(tokens.pop())
        with repo.engine.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(job_imports)) == 2
    finally:
        while tokens:
            reset_user(tokens.pop())
