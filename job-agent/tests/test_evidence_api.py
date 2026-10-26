from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import event, func, select

from app.api import applications
from app.core.database_schema import application_sources
from app.main import app
from app.services.application_repository import ApplicationRepository
from tests.test_applications_api import application_payload, use_temporary_repository

client = TestClient(app)
RESUME_TEXT = "教育背景：示例大学。\n使用 Python 和 FastAPI 开发接口，并编写测试。"
JOB_TEXT = "负责业务接口开发与自动化测试。熟悉 Python 和 SQL。"


def _version_payload(resume_line: str = "使用 Python 和 FastAPI 开发接口，并编写测试。") -> dict:
    return {
        "resume": {"title": "人工简历", "sections": [{"heading": "项目经历", "lines": [
            resume_line, "负责业务接口开发与自动化测试。", "带领十人团队获得冠军。", "Python",
        ]}]},
        "cover_letter": {"title": "人工求职信", "sections": [{"heading": "正文", "lines": [
            "期待进一步交流。",
        ]}]},
    }


def test_source_retention_requires_explicit_consent(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    payload = application_payload()
    payload["resume_text"] = RESUME_TEXT
    payload["job_description"] = JOB_TEXT
    assert client.post("/api/applications", json=payload).status_code == 422
    payload["retain_source_text"] = True
    del payload["job_description"]
    assert client.post("/api/applications", json=payload).status_code == 422

    plain = client.post("/api/applications", json=application_payload())
    assert plain.status_code == 201
    record_id = plain.json()["id"]
    assert "resume_text" not in plain.json()
    assert client.get(f"/api/applications/{record_id}/sources/status").json() == {
        "retained": False,
    }
    assert client.get("/api/applications/999/sources/status").status_code == 404
    assert client.post(f"/api/applications/{record_id}/draft-versions",
                       json=_version_payload()).status_code == 201
    assert client.get(f"/api/applications/{record_id}/draft-versions/1/evidence").status_code == 409


def test_evidence_report_is_literal_and_scoped_to_application(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    consented = application_payload()
    consented.update(retain_source_text=True, resume_text=RESUME_TEXT,
                     job_description=JOB_TEXT)
    response = client.post("/api/applications", json=consented)
    assert response.status_code == 201
    first_id = response.json()["id"]
    assert "resume_text" not in response.json()
    assert client.get(f"/api/applications/{first_id}/sources/status").json()["retained"]
    assert client.post(f"/api/applications/{first_id}/draft-versions",
                       json=_version_payload()).status_code == 201

    report_response = client.get(f"/api/applications/{first_id}/draft-versions/1/evidence")
    assert report_response.status_code == 200
    assert report_response.headers["cache-control"] == "no-store"
    report = report_response.json()
    assert (report["resume_hits"], report["job_hits"], report["unmatched"]) == (1, 1, 3)
    assert [line["source"] for line in report["lines"]] == [
        "resume", "job", None, None, None,
    ]
    assert "使用 Python 和 FastAPI" in report["lines"][0]["source_excerpt"]
    assert report["lines"][0]["source_offset"] == RESUME_TEXT.index("使用 Python")
    assert "不证明" in report["warning"]

    # 相同候选人画像被复用，也不能借用另一投递记录的原文。
    second = client.post("/api/applications", json=application_payload())
    second_id = second.json()["id"]
    assert client.post(f"/api/applications/{second_id}/draft-versions",
                       json=_version_payload()).status_code == 201
    assert client.get(f"/api/applications/{second_id}/draft-versions/1/evidence").status_code == 409
    assert client.get(f"/api/applications/{first_id}/draft-versions/2/evidence").status_code == 404

    assert client.delete(f"/api/applications/{first_id}/sources").status_code == 204
    assert not client.get(f"/api/applications/{first_id}/sources/status").json()["retained"]
    assert client.get(f"/api/applications/{first_id}/draft-versions/1/evidence").status_code == 409
    assert client.get(f"/api/applications/{first_id}").status_code == 200


def test_compare_versions_shows_text_changes(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    record_id = client.post("/api/applications", json=application_payload()).json()["id"]
    base = f"/api/applications/{record_id}/draft-versions"
    assert client.post(base, json=_version_payload()).status_code == 201
    assert client.post(base, json=_version_payload("使用 Python 开发后端服务。")).status_code == 201
    compared = client.get(f"{base}/compare", params={"from_version": 1, "to_version": 2})
    assert compared.status_code == 200
    assert compared.headers["cache-control"] == "no-store"
    diff = compared.json()
    assert any(line.startswith("-使用 Python 和 FastAPI") for line in diff["resume_diff"])
    assert any(line.startswith("+使用 Python 开发后端服务") for line in diff["resume_diff"])
    assert diff["cover_letter_diff"] == []
    assert client.get(f"{base}/compare", params={"from_version": 1,
                                                  "to_version": 99}).status_code == 404


def test_deleting_application_cascades_retained_sources(monkeypatch, tmp_path: Path) -> None:
    repo = ApplicationRepository(f"sqlite+pysqlite:///{(tmp_path / 'source-cascade.db').as_posix()}")
    repo.engine.dispose()

    @event.listens_for(repo.engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    monkeypatch.setattr(applications, "get_repository", lambda: repo)
    payload = application_payload()
    payload.update(retain_source_text=True, resume_text=RESUME_TEXT,
                   job_description=JOB_TEXT)
    record_id = client.post("/api/applications", json=payload).json()["id"]
    assert client.delete(f"/api/applications/{record_id}").status_code == 204
    with repo.engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(application_sources)) == 0
    repo.engine.dispose()
