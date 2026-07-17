from typing import Literal

from fastapi.testclient import TestClient

from app.api import jobs, matches
from app.main import app
from app.models.job import JobProfile
from app.models.match import MatchResult

client = TestClient(app)


class FakeJobAnalyzer:
    provider: Literal["openai", "deepseek"] = "deepseek"
    model = "job-test"

    async def analyze(self, description: str) -> JobProfile:
        assert "Python" in description
        return JobProfile(title="后端开发实习生", required_skills=["Python"])


class FakeMatchAnalyzer:
    provider: Literal["openai", "deepseek"] = "openai"
    model = "match-test"

    async def analyze(self, candidate, job) -> MatchResult:
        assert candidate.basic_info.name == "张晨"
        assert job.title == "后端开发实习生"
        return MatchResult.model_validate(
            {
                "overall_score": 82,
                "recommendation": "建议投递",
                "summary": "核心技能匹配。",
                "dimensions": [
                    {"name": "技能匹配", "score": 90, "weight": 35, "reason": "Python 匹配"},
                    {"name": "项目经验", "score": 80, "weight": 25, "reason": "有项目"},
                    {"name": "教育背景", "score": 80, "weight": 15, "reason": "符合"},
                    {"name": "实习经历", "score": 70, "weight": 15, "reason": "较少"},
                    {"name": "基本条件", "score": 85, "weight": 10, "reason": "基本符合"},
                ],
                "assessments": [],
                "strengths": ["Python"],
                "gaps": [],
                "resume_suggestions": ["突出后端项目"],
                "warnings": [],
            }
        )


def test_parse_job(monkeypatch) -> None:
    selected = []
    monkeypatch.setattr(
        jobs,
        "build_job_analyzer",
        lambda provider=None: selected.append(provider) or FakeJobAnalyzer(),
    )
    response = client.post(
        "/api/jobs/parse",
        json={"description": "招聘 Python 后端开发实习生，要求熟悉 FastAPI。", "provider": "deepseek"},
    )
    assert response.status_code == 200
    assert response.json()["profile"]["title"] == "后端开发实习生"
    assert selected == ["deepseek"]


def test_parse_job_rejects_short_description() -> None:
    response = client.post("/api/jobs/parse", json={"description": "太短"})
    assert response.status_code == 422


def test_analyze_match(monkeypatch) -> None:
    monkeypatch.setattr(matches, "build_match_analyzer", lambda provider=None: FakeMatchAnalyzer())
    response = client.post(
        "/api/matches/analyze",
        json={
            "provider": "openai",
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
            "job_profile": {"title": "后端开发实习生"},
        },
    )
    assert response.status_code == 200
    assert response.json()["result"]["overall_score"] == 82
    assert response.json()["result"]["recommendation"] == "建议投递"
