from fastapi.testclient import TestClient

from app.api import discovery
from app.main import app
from app.models.job import JobProfile
from app.services.application_repository import ApplicationRepository
from app.services.discovery_repository import DiscoveryRepository
from app.services.job_discovery import PostingNotFoundError
from app.services.library_repository import LibraryRepository
from scripts.upgrade_job_imports import upgrade

client = TestClient(app)


def use_temporary_discovery(monkeypatch, tmp_path):
    path = (tmp_path / "discovery.db").as_posix()
    application_repository = ApplicationRepository(f"sqlite+pysqlite:///{path}")
    repository = DiscoveryRepository(application_repository.engine)
    monkeypatch.setattr(discovery, "get_discovery_repository", lambda: repository)
    monkeypatch.setattr(discovery, "get_library_repository",
                        lambda: LibraryRepository(application_repository.engine))
    return application_repository.engine


def test_greenhouse_filter_import_source_and_duplicate(monkeypatch, tmp_path):
    use_temporary_discovery(monkeypatch, tmp_path)
    calls = []

    def fake_fetch(url):
        calls.append(url)
        intern = {
            "id": 101, "title": "Python Intern", "company_name": "星云科技",
            "location": {"name": "Shanghai"},
            "absolute_url": "https://boards.greenhouse.io/demo/jobs/101",
            "content": "<p>Python 实习岗位，负责接口开发和自动化测试。</p>",
        }
        fulltime = {
            "id": 102, "title": "Sales Manager", "location": {"name": "Beijing"},
            "absolute_url": "https://boards.greenhouse.io/demo/jobs/102",
            "content": "<p>负责销售团队管理。</p>",
        }
        return intern if "/jobs/101" in url else {"jobs": [intern, fulltime]}

    from app.services import job_discovery
    monkeypatch.setattr(job_discovery, "fetch_json", fake_fetch)
    search = client.post("/api/discovery/search", json={
        "source": "greenhouse", "board_token": "demo", "keyword": "Python",
        "location": "Shanghai", "internship_only": True,
    })
    assert search.status_code == 200
    assert search.json()["scanned"] == 2
    assert [item["external_id"] for item in search.json()["items"]] == ["101"]
    assert search.json()["items"][0]["imported_job_id"] is None

    class FakeAnalyzer:
        async def analyze(self, description):
            assert "接口开发" in description
            return JobProfile(required_skills=["Python"])

    analyzed = []

    def fake_analyzer(provider):
        analyzed.append(provider)
        return FakeAnalyzer()

    monkeypatch.setattr(discovery, "build_job_analyzer", fake_analyzer)
    imported = client.post("/api/discovery/imports", json={
        "source": "greenhouse", "board_token": "demo", "external_id": "101",
        "llm_provider": "deepseek",
    })
    assert imported.status_code == 200
    assert imported.json()["created"] is True
    assert imported.json()["record"]["title"] == "Python Intern"
    assert imported.json()["record"]["company"] == "星云科技"
    assert analyzed == ["deepseek"]
    job_id = imported.json()["record"]["job_id"]

    duplicate = client.post("/api/discovery/imports", json={
        "source": "greenhouse", "board_token": "demo", "external_id": "101",
        "llm_provider": "openai",
    })
    assert duplicate.json()["created"] is False
    assert duplicate.json()["record"]["job_id"] == job_id
    assert analyzed == ["deepseek"]  # 重复来源不再调用模型。
    assert len(client.get("/api/discovery/imports").json()) == 1
    refreshed = client.post("/api/discovery/search", json={
        "source": "greenhouse", "board_token": "demo",
    })
    assert refreshed.json()["items"][0]["imported_job_id"] == job_id
    assert all("boards-api.greenhouse.io" in url for url in calls)


def test_lever_public_feed_and_input_validation(monkeypatch, tmp_path):
    use_temporary_discovery(monkeypatch, tmp_path)

    def fake_fetch(url):
        if "/missing" in url:
            raise PostingNotFoundError("该招聘板不存在。")
        return [{
            "id": "a-b-c", "text": "Software Engineering Intern",
            "categories": {"location": "Remote", "commitment": "Intern"},
            "descriptionPlain": "Build Python services and write tests.",
            "hostedUrl": "https://jobs.lever.co/demo/a-b-c",
        }]

    from app.services import job_discovery
    monkeypatch.setattr(job_discovery, "fetch_json", fake_fetch)
    response = client.post("/api/discovery/search", json={
        "source": "lever", "board_token": "demo", "location": "remote",
        "internship_only": True,
    })
    assert response.status_code == 200
    assert response.json()["items"][0]["commitment"] == "Intern"
    assert client.post("/api/discovery/search", json={
        "source": "lever", "board_token": "../private",
    }).status_code == 422
    assert client.post("/api/discovery/imports", json={
        "source": "lever", "board_token": "demo", "external_id": "../private",
    }).status_code == 422
    assert client.post("/api/discovery/search", json={
        "source": "lever", "board_token": "missing",
    }).status_code == 404


def test_mysql_upgrade_script_rejects_sqlite(monkeypatch, tmp_path):
    engine = use_temporary_discovery(monkeypatch, tmp_path)
    try:
        upgrade(engine)
    except ValueError as exc:
        assert "MySQL" in str(exc)
    else:
        raise AssertionError("SQLite 不能执行 MySQL 增量升级脚本")
