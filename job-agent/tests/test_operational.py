"""就绪检查和不含敏感信息的访问日志。"""

import logging

from fastapi.testclient import TestClient

from app.api import applications
from app.main import app
from app.services.application_repository import ApplicationRepository
from app.services.auth_repository import AuthRepository


def test_ready_requires_initialized_account(monkeypatch, tmp_path) -> None:
    repo = ApplicationRepository(f"sqlite+pysqlite:///{(tmp_path / 'ready.db').as_posix()}")
    monkeypatch.setattr(applications, "get_repository", lambda: repo)
    with TestClient(app) as client:
        unavailable = client.get("/ready")
        assert unavailable.status_code == 503
        assert unavailable.json() == {"status": "unavailable"}
        assert unavailable.headers["cache-control"] == "no-store"
        AuthRepository(repo.engine).create_user("ready_owner", "StrongReadyPassphrase-A1")
        ready = client.get("/ready")
        assert ready.status_code == 200
        assert ready.json() == {"status": "ready"}


def test_access_log_omits_query_and_credentials(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="uvicorn.error"), TestClient(app) as client:
        response = client.get("/upload?private_note=do-not-log",
                              headers={"Cookie": "session=do-not-log"})
    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    assert len(request_id) == 32
    lines = [item.message for item in caplog.records if "request_id=" in item.message]
    assert any(request_id in line and "route=/upload" in line for line in lines)
    assert all("do-not-log" not in line and "private_note" not in line for line in lines)
