from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.api import applications
from app.core.database_schema import applications_table
from app.main import app
from app.services.application_repository import ApplicationRepository

client = TestClient(app)


def application_payload() -> dict:
    return {
        "resume_filename": "测试简历.txt",
        "candidate_profile": {
            "basic_info": {"name": "张晨", "links": []},
            "job_targets": [],
            "education": [],
            "skills": [],
            "projects": [],
            "experiences": [],
            "certificates": [],
            "warnings": [],
        },
        "job_profile": {
            "title": "Python 后端开发实习生",
            "company": "星云科技",
            "location": "上海",
        },
        "match_result": {
            "overall_score": 82,
            "recommendation": "建议投递",
            "summary": "核心技能匹配。",
            "dimensions": [
                {"name": "技能匹配", "score": 90, "weight": 35, "reason": "符合"},
                {"name": "项目经验", "score": 80, "weight": 25, "reason": "符合"},
                {"name": "教育背景", "score": 80, "weight": 15, "reason": "符合"},
                {"name": "实习经历", "score": 70, "weight": 15, "reason": "较少"},
                {"name": "基本条件", "score": 85, "weight": 10, "reason": "符合"},
            ],
            "assessments": [],
            "strengths": ["Python"],
            "gaps": [],
            "resume_suggestions": [],
            "warnings": [],
        },
        "provider": "openai",
        "model": "gpt-test",
        "status": "待投递",
        "job_url": "https://example.com/jobs/1",
        "notes": "周五前投递",
    }


def use_temporary_repository(monkeypatch, tmp_path) -> None:
    database_path = (tmp_path / "applications.db").as_posix()
    repository = ApplicationRepository(f"sqlite+pysqlite:///{database_path}")
    monkeypatch.setattr(applications, "get_repository", lambda: repository)


def test_application_crud(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)

    created = client.post("/api/applications", json=application_payload())
    assert created.status_code == 201
    record_id = created.json()["id"]

    listed = client.get("/api/applications", params={"status": "待投递", "sort": "score_desc"})
    assert listed.status_code == 200
    assert listed.json()[0]["company"] == "星云科技"
    assert listed.json()[0]["overall_score"] == 82

    updated = client.patch(
        f"/api/applications/{record_id}",
        json={"status": "面试", "notes": "一面时间待确认"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "面试"
    assert updated.json()["notes"] == "一面时间待确认"

    detail = client.get(f"/api/applications/{record_id}")
    assert detail.status_code == 200
    assert detail.json()["match_result"]["overall_score"] == 82

    deleted = client.delete(f"/api/applications/{record_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/applications/{record_id}").status_code == 404


def test_application_rejects_invalid_status(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    payload = application_payload()
    payload["status"] = "随便看看"
    response = client.post("/api/applications", json=payload)
    assert response.status_code == 422


def test_search_filter_sort_and_pagination(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    record_ids = []
    for index, (company, score, status) in enumerate([
        ("星云科技", 82, "待投递"), ("云海实验室", 91, "已投递"),
        ("星云数据", 77, "待投递"),
    ]):
        payload = application_payload()
        payload["job_profile"]["company"] = company
        payload["job_profile"]["title"] = f"岗位 {index}"
        payload["match_result"]["overall_score"] = score
        payload["status"] = status
        created = client.post("/api/applications", json=payload)
        assert created.status_code == 201
        record_ids.append(created.json()["id"])

    # 旧快照即使没有岗位和报告关联，也应能被搜索与评分排序查到。
    with applications.get_repository().engine.begin() as connection:
        connection.execute(update(applications_table).where(
            applications_table.c.id == record_ids[2],
        ).values(job_id=None, match_report_id=None))

    first = client.get("/api/applications/search", params={
        "q": "星云", "status": "待投递", "sort": "score_desc", "page_size": 1,
    })
    assert first.status_code == 200
    assert first.json()["total"] == 2
    assert first.json()["items"][0]["company"] == "星云科技"
    second = client.get("/api/applications/search", params={
        "q": "星云", "status": "待投递", "sort": "score_desc", "page_size": 1, "page": 2,
    })
    assert second.json()["items"][0]["company"] == "星云数据"
    assert client.get("/api/applications/search", params={"q": "不存在"}).json()["total"] == 0
    assert client.get("/api/applications/search", params={"page": 0}).status_code == 422
    assert client.get("/api/applications/search", params={"page_size": 101}).status_code == 422


def test_history_events_and_manual_applied_date(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    created = client.post("/api/applications", json=application_payload()).json()
    record_id = created["id"]
    assert created["applied_at"] is None
    changed = client.patch(f"/api/applications/{record_id}", json={
        "status": "已投递", "applied_at": "2026-10-20",
    })
    assert changed.status_code == 200
    assert changed.json()["applied_at"] == "2026-10-20"
    events = client.get(f"/api/applications/{record_id}/events")
    assert events.status_code == 200
    assert [item["event_type"] for item in events.json()] == [
        "applied_at_changed", "status_changed", "created",
    ]
    assert client.get(f"/api/applications/{record_id}").json()["match_result"]["overall_score"] == 82

    cleared = client.patch(f"/api/applications/{record_id}", json={"applied_at": None})
    assert cleared.status_code == 200
    assert cleared.json()["applied_at"] is None
    assert client.get(f"/api/applications/{record_id}/events").json()[0]["event_type"] == "applied_at_changed"
    assert client.patch(f"/api/applications/{record_id}", json={
        "notes": "日期待核对",
    }).json()["applied_at"] is None
    assert client.get("/api/applications/999/events").status_code == 404


def test_status_change_auto_dates_only_when_missing(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    record_id = client.post("/api/applications", json=application_payload()).json()["id"]
    changed = client.patch(f"/api/applications/{record_id}", json={"status": "已投递"})
    assert changed.status_code == 200
    assert changed.json()["applied_at"] is not None
    custom = client.patch(f"/api/applications/{record_id}", json={"applied_at": "2026-10-20"})
    assert custom.json()["applied_at"] == "2026-10-20"
    later = client.patch(f"/api/applications/{record_id}", json={"notes": "已补日期"})
    assert later.json()["applied_at"] == "2026-10-20"
