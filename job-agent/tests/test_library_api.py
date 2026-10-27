from fastapi.testclient import TestClient

from app.api import applications, library
from app.main import app
from app.models.match import MatchResult
from app.services.application_repository import ApplicationRepository
from app.services.library_repository import LibraryRepository
from scripts.upgrade_job_favorites import upgrade
from tests.test_applications_api import application_payload

client = TestClient(app)


def use_temporary_library(monkeypatch, tmp_path) -> None:
    database_path = (tmp_path / "library.db").as_posix()
    application_repository = ApplicationRepository(f"sqlite+pysqlite:///{database_path}")
    repository = LibraryRepository(application_repository.engine)
    monkeypatch.setattr(applications, "get_repository", lambda: application_repository)
    monkeypatch.setattr(library, "get_library_repository", lambda: repository)


def test_asset_save_dedup_favorites_and_delete(monkeypatch, tmp_path) -> None:
    use_temporary_library(monkeypatch, tmp_path)
    payload = application_payload()
    resume = {"filename": "我的简历.txt", "profile": payload["candidate_profile"]}
    first = client.post("/api/library/resumes", json=resume)
    assert first.status_code == 200
    assert first.json()["created"] is True
    second = client.post("/api/library/resumes", json=resume)
    assert second.json()["created"] is False
    resume_id = first.json()["asset"]["id"]
    assert len(client.get("/api/library/resumes").json()) == 1
    assert client.get(f"/api/library/resumes/{resume_id}").json()["profile"]["basic_info"]["name"] == "张晨"

    job = {"profile": payload["job_profile"], "job_url": "https://example.com/jobs/1",
           "favorite": True}
    saved = client.post("/api/library/jobs", json=job)
    assert saved.status_code == 200
    assert saved.json()["asset"]["favorite"] is True
    job_id = saved.json()["asset"]["id"]
    duplicate = client.post("/api/library/jobs", json={**job, "job_url": "https://example.com/jobs/1/"})
    assert duplicate.json()["created"] is False
    assert duplicate.json()["asset"]["id"] == job_id
    assert len(client.get("/api/library/jobs", params={"favorite_only": True}).json()) == 1
    unfavorite = client.patch(f"/api/library/jobs/{job_id}/favorite", json={"favorite": False})
    assert unfavorite.json()["favorite"] is False
    assert client.get("/api/library/jobs", params={"favorite_only": True}).json() == []
    assert client.get(f"/api/library/jobs/{job_id}").status_code == 200
    assert client.delete(f"/api/library/jobs/{job_id}").status_code == 204
    assert client.delete(f"/api/library/resumes/{resume_id}").status_code == 204
    assert client.get(f"/api/library/jobs/{job_id}").status_code == 404
    assert client.get(f"/api/library/resumes/{resume_id}").status_code == 404


def test_reports_history_and_reanalysis_do_not_change_application(monkeypatch, tmp_path) -> None:
    use_temporary_library(monkeypatch, tmp_path)
    payload = application_payload()
    created = client.post("/api/applications", json=payload)
    assert created.status_code == 201
    application_id = created.json()["id"]
    resume = client.post("/api/library/resumes", json={
        "filename": payload["resume_filename"], "profile": payload["candidate_profile"],
    }).json()
    job = client.post("/api/library/jobs", json={
        "profile": payload["job_profile"], "job_url": payload["job_url"],
    }).json()
    assert resume["created"] is False
    assert job["created"] is False
    resume_id, job_id = resume["asset"]["id"], job["asset"]["id"]
    assert client.delete(f"/api/library/resumes/{resume_id}").status_code == 409
    assert client.delete(f"/api/library/jobs/{job_id}").status_code == 409

    class FakeAnalyzer:
        provider = "deepseek"
        model = "fake-model"

        async def analyze(self, candidate, target):
            assert candidate.basic_info.name == "张晨"
            assert target.company == "星云科技"
            return MatchResult.model_validate({**payload["match_result"], "overall_score": 90})

    monkeypatch.setattr(library, "build_match_analyzer", lambda provider: FakeAnalyzer())
    new_report = client.post("/api/library/reports/reanalyze", json={
        "resume_id": resume_id, "job_id": job_id, "provider": "deepseek",
    })
    assert new_report.status_code == 201
    assert new_report.json()["overall_score"] == 90
    reports = client.get("/api/library/reports", params={
        "resume_id": resume_id, "job_id": job_id,
    })
    assert reports.status_code == 200
    assert [report["overall_score"] for report in reports.json()] == [90, 82]
    report_id = new_report.json()["id"]
    assert client.get(f"/api/library/reports/{report_id}").json()["result"]["overall_score"] == 90
    assert client.get(f"/api/applications/{application_id}").json()["match_result"]["overall_score"] == 82
    assert client.post("/api/library/reports/reanalyze", json={
        "resume_id": 999, "job_id": job_id,
    }).status_code == 404


def test_library_validation_and_missing_assets(monkeypatch, tmp_path) -> None:
    use_temporary_library(monkeypatch, tmp_path)
    assert client.get("/api/library/jobs/999").status_code == 404
    assert client.get("/api/library/reports/999").status_code == 404
    assert client.patch("/api/library/jobs/999/favorite", json={"favorite": True}).status_code == 404
    assert client.post("/api/library/jobs", json={
        "profile": application_payload()["job_profile"], "job_url": "javascript:alert(1)",
    }).status_code == 422
    assert client.get("/api/library/reports", params={"resume_id": 0}).status_code == 422


def test_mysql_upgrade_script_rejects_sqlite(monkeypatch, tmp_path) -> None:
    use_temporary_library(monkeypatch, tmp_path)
    try:
        upgrade(library.get_library_repository().engine)
    except ValueError as exc:
        assert "MySQL" in str(exc)
    else:
        raise AssertionError("SQLite 不能执行 MySQL 增量升级脚本")
