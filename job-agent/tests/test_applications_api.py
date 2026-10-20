from pathlib import Path

from fastapi.testclient import TestClient

from app.api import applications
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
