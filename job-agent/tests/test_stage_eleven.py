"""第十一阶段：模板、逐行人工关联和风险提示。"""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, select

from app.api import applications
from app.core.database_schema import draft_annotations
from app.main import app
from app.services.application_repository import ApplicationRepository
from scripts.upgrade_draft_annotations import upgrade
from tests.test_applications_api import application_payload, use_temporary_repository

client = TestClient(app)
RESUME = "教育背景：示例大学。使用 Python 和 FastAPI 开发接口，并编写测试。"
JOB = "负责业务接口开发与自动化测试。熟悉 Python 和 SQL。"


def _record(retain: bool = True) -> int:
    payload = application_payload()
    if retain:
        payload.update(retain_source_text=True, resume_text=RESUME, job_description=JOB)
    response = client.post("/api/applications", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _version(record_id: int) -> None:
    documents = {
        "resume": {"title": "简历", "sections": [{"heading": "项目", "lines": [
            "使用 Python 和 FastAPI 开发接口，并编写测试。",
            "负责业务接口开发与自动化测试。", "自称获得冠军。",
        ]}]},
        "cover_letter": {"title": "求职信", "sections": [{"heading": "正文", "lines": [
            "期待进一步交流。",
        ]}]},
    }
    assert client.post(f"/api/applications/{record_id}/draft-versions",
                       json=documents).status_code == 201


def test_compact_template_is_distinct_and_default_is_stable(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    payload = application_payload()
    payload["candidate_profile"]["skills"] = [
        {"name": f"技能{index}", "category": "其他"} for index in range(7)
    ]
    record_id = client.post("/api/applications", json=payload).json()["id"]
    base = f"/api/applications/{record_id}/draft"
    standard = client.get(base).json()
    compact = client.get(base, params={"template": "compact"}).json()
    assert standard["template"] == "standard"
    assert compact["template"] == "compact"
    assert len(next(s for s in standard["resume"]["sections"] if s["heading"] == "技能")["lines"]) == 7
    assert len(next(s for s in compact["resume"]["sections"] if s["heading"] == "技能")["lines"]) == 5
    assert "精简模板" in " ".join(compact["warnings"])
    assert client.get(base, params={"template": "unknown"}).status_code == 422
    download = client.get(f"{base}/resume.docx", params={"template": "compact"})
    assert download.status_code == 200 and download.content.startswith(b"PK")


def test_annotation_requires_retained_literal_and_is_deleted_with_source(
    monkeypatch, tmp_path: Path,
) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    record_id = _record()
    _version(record_id)
    base = f"/api/applications/{record_id}/draft-versions/1"
    report = client.get(f"{base}/evidence").json()
    assert report["job_as_resume"] == 1
    assert [line["attention"] for line in report["lines"]] == [
        "literal_only", "job_as_resume", "review", "review",
    ]
    data = {"document": "resume", "section_index": 0, "line_index": 2,
            "source_kind": "resume", "source_quote": "使用 Python 和 FastAPI 开发接口",
            "note": "需本人核对夸大表述"}
    assert client.put(f"{base}/annotations", json={**data, "source_quote": "不存在的原文片段"}).status_code == 422
    assert client.put(f"{base}/annotations", json={**data, "line_index": 8}).status_code == 422
    assert client.put(f"{base}/annotations", json={**data, "source_kind": "job"}).status_code == 422
    created = client.put(f"{base}/annotations", json=data)
    assert created.status_code == 200
    assert created.headers["cache-control"] == "no-store"
    assert client.put(f"{base}/annotations", json={**data, "note": "二次核对"}).json()[
        "id"] == created.json()["id"]
    report = client.get(f"{base}/evidence").json()
    assert report["lines"][2]["annotation"]["note"] == "二次核对"
    assert report["lines"][2]["attention"] == "review"
    assert client.delete(f"/api/applications/{record_id}/sources").status_code == 204
    with applications.get_repository().engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(draft_annotations)) == 0
    assert client.get(f"{base}/evidence").status_code == 409
    assert client.put(f"{base}/annotations", json=data).status_code == 409


def test_annotations_are_version_and_application_scoped(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    first = _record()
    second = _record(retain=False)
    _version(first)
    _version(second)
    data = {"document": "resume", "section_index": 0, "line_index": 0,
            "source_kind": "resume", "source_quote": "使用 Python 和 FastAPI 开发接口"}
    first_base = f"/api/applications/{first}/draft-versions/1"
    second_base = f"/api/applications/{second}/draft-versions/1"
    assert client.put(f"{second_base}/annotations", json=data).status_code == 409
    assert client.put(f"/api/applications/{first}/draft-versions/2/annotations",
                      json=data).status_code == 404
    assert client.put(f"{first_base}/annotations", json=data).status_code == 200
    assert client.get(f"{second_base}/evidence").status_code == 409
    assert client.delete(f"{first_base}/annotations", params={
        "document": "resume", "section_index": 0, "line_index": 0,
    }).status_code == 204
    assert client.get(f"{first_base}/evidence").json()["lines"][0]["annotation"] is None


def test_deleting_application_cascades_annotations(monkeypatch, tmp_path: Path) -> None:
    repo = ApplicationRepository(f"sqlite+pysqlite:///{(tmp_path / 'annotation-cascade.db').as_posix()}")
    repo.engine.dispose()

    @event.listens_for(repo.engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    monkeypatch.setattr(applications, "get_repository", lambda: repo)
    record_id = _record()
    _version(record_id)
    base = f"/api/applications/{record_id}/draft-versions/1"
    data = {"document": "resume", "section_index": 0, "line_index": 0,
            "source_kind": "resume", "source_quote": "使用 Python 和 FastAPI 开发接口"}
    assert client.put(f"{base}/annotations", json=data).status_code == 200
    assert client.delete(f"/api/applications/{record_id}").status_code == 204
    with repo.engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(draft_annotations)) == 0
    repo.engine.dispose()


def test_mysql_annotation_upgrade_refuses_sqlite(tmp_path: Path) -> None:
    repo = ApplicationRepository(f"sqlite+pysqlite:///{(tmp_path / 'upgrade.db').as_posix()}")
    with pytest.raises(ValueError, match="只用于 MySQL"):
        upgrade(repo.engine)
    repo.engine.dispose()
