"""第十二阶段：投递日程、站内提醒和已确认材料的面试准备。"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select

from app.api import applications
from app.core.database_schema import application_milestones
from app.main import app
from app.services.application_repository import ApplicationRepository
from scripts.upgrade_application_milestones import upgrade
from tests.test_applications_api import application_payload, use_temporary_repository

client = TestClient(app)


def _create_record() -> int:
    response = client.post("/api/applications", json=application_payload())
    assert response.status_code == 201
    return response.json()["id"]


def _create_milestone(record_id: int, kind: str, when: datetime) -> dict:
    response = client.post(f"/api/planning/applications/{record_id}/milestones", json={
        "kind": kind, "title": "测试安排", "scheduled_at": when.isoformat(), "notes": "准备材料",
    })
    assert response.status_code == 201
    return response.json()


def test_milestones_reminders_completion_and_scope(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    first = _create_record()
    second = _create_record()
    now = datetime.now(UTC)
    deadline = _create_milestone(first, "deadline", now - timedelta(days=1))
    interview = _create_milestone(first, "interview", now + timedelta(days=2))
    later = _create_milestone(second, "follow_up", now + timedelta(days=20))
    assert deadline["reminder_state"] == "overdue"
    assert interview["reminder_state"] == "soon"
    assert later["reminder_state"] == "later"
    rescheduled = client.patch(f"/api/planning/applications/{first}/milestones/{interview['id']}",
                               json={"title": "技术面试", "scheduled_at": (
                                   now + timedelta(days=3)).isoformat(), "notes": None})
    assert rescheduled.status_code == 200
    assert rescheduled.json()["title"] == "技术面试"
    assert rescheduled.json()["notes"] is None
    reminders = client.get("/api/planning/reminders", params={"days": 7}).json()
    assert [item["id"] for item in reminders["items"]] == [deadline["id"], interview["id"]]
    assert reminders["truncated"] is False
    base = f"/api/planning/applications/{first}/milestones"
    assert len(client.get(base).json()) == 2
    assert client.get(f"/api/planning/applications/{second}/milestones").json()[0]["id"] == later["id"]
    assert client.patch(f"{base}/{later['id']}", json={"completed": True}).status_code == 404
    completed = client.patch(f"{base}/{deadline['id']}", json={"completed": True}).json()
    assert completed["reminder_state"] == "completed" and completed["completed_at"]
    repeated = client.patch(f"{base}/{deadline['id']}", json={"completed": True}).json()
    assert repeated["completed_at"] == completed["completed_at"]
    assert len(client.get("/api/planning/reminders").json()["items"]) == 1
    assert client.patch(f"{base}/{deadline['id']}", json={"completed": False}).json()[
        "reminder_state"] == "overdue"
    assert client.delete(f"{base}/{deadline['id']}").status_code == 204
    assert client.delete(f"{base}/{deadline['id']}").status_code == 404


def test_planning_rejects_invalid_time_and_empty_changes(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    record_id = _create_record()
    base = f"/api/planning/applications/{record_id}/milestones"
    assert client.post(base, json={"kind": "interview", "title": "面试",
                                   "scheduled_at": "2026-11-01T10:00:00"}).status_code == 422
    assert client.post(base, json={"kind": "unknown", "title": "无效",
                                   "scheduled_at": datetime.now(UTC).isoformat()}).status_code == 422
    assert client.post("/api/planning/applications/999/milestones", json={
        "kind": "deadline", "title": "截止", "scheduled_at": datetime.now(UTC).isoformat(),
    }).status_code == 404
    created = _create_milestone(record_id, "interview", datetime.now(UTC))
    assert client.patch(f"{base}/{created['id']}", json={}).status_code == 422
    assert client.patch(f"{base}/{created['id']}", json={"title": None}).status_code == 422
    assert client.get("/api/planning/reminders", params={"days": 31}).status_code == 422


def test_interview_preparation_uses_confirmed_version_only(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    payload = application_payload()
    payload["candidate_profile"]["skills"] = [{"name": "Python", "category": "编程语言"}]
    payload["job_profile"]["required_skills"] = ["Python", "SQL"]
    payload["match_result"]["gaps"] = ["数据库实践不足"]
    record_id = client.post("/api/applications", json=payload).json()["id"]
    draft = client.get(f"/api/applications/{record_id}/draft").json()
    versions = f"/api/applications/{record_id}/draft-versions"
    assert client.post(versions, json={"resume": draft["resume"],
                                      "cover_letter": draft["cover_letter"]}).status_code == 201
    prep = f"/api/planning/applications/{record_id}/interview-prep"
    assert client.get(prep, params={"version": 1}).status_code == 409
    assert client.patch(f"{versions}/1/review", json={"confirmed": True}).status_code == 200
    response = client.get(prep, params={"version": 1})
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    result = response.json()
    assert result["version"] == 1
    assert any(item["focus"] == "Python" and item["reviewed_material_lines"]
               for item in result["prompts"])
    assert any(item["focus"] == "SQL" and item["needs_example"]
               for item in result["prompts"])
    assert any("数据库实践不足" in item["question"] for item in result["prompts"])
    assert client.get(prep, params={"version": 2}).status_code == 404


def test_deleting_application_cascades_milestones(monkeypatch, tmp_path: Path) -> None:
    repo = ApplicationRepository(f"sqlite+pysqlite:///{(tmp_path / 'schedule-cascade.db').as_posix()}")
    repo.engine.dispose()

    @event.listens_for(repo.engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    monkeypatch.setattr(applications, "get_repository", lambda: repo)
    record_id = _create_record()
    _create_milestone(record_id, "deadline", datetime.now(UTC))
    assert client.delete(f"/api/applications/{record_id}").status_code == 204
    with repo.engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(application_milestones)) == 0
    repo.engine.dispose()


def test_mysql_schedule_upgrade_refuses_sqlite(tmp_path: Path) -> None:
    repo = ApplicationRepository(f"sqlite+pysqlite:///{(tmp_path / 'schedule-upgrade.db').as_posix()}")
    with pytest.raises(ValueError, match="只用于 MySQL"):
        upgrade(repo.engine)
    repo.engine.dispose()
