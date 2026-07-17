from typing import Literal

from fastapi.testclient import TestClient

from app.api import resumes
from app.core.config import LLMConfigurationError
from app.main import app
from app.models.candidate import CandidateProfile

client = TestClient(app)


class FakeAnalyzer:
    provider: Literal["openai", "deepseek"] = "openai"
    model = "gpt-test"

    async def analyze(self, resume_text: str) -> CandidateProfile:
        assert "张晨" in resume_text
        return CandidateProfile.model_validate(
            {
                "basic_info": {"name": "张晨", "links": []},
                "job_targets": ["Python 后端开发实习生"],
                "summary": "计算机科学本科生",
                "education": [],
                "skills": [],
                "projects": [],
                "experiences": [],
                "certificates": [],
                "warnings": [],
            }
        )


def test_analyze_resume_returns_structured_profile(monkeypatch) -> None:
    monkeypatch.setattr(resumes, "build_resume_analyzer", lambda: FakeAnalyzer())

    response = client.post(
        "/api/resumes/analyze",
        files={"file": ("resume.txt", "张晨\nPython 后端开发实习生".encode(), "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-test"
    assert data["profile"]["basic_info"]["name"] == "张晨"


def test_analyze_resume_reports_missing_api_key(monkeypatch) -> None:
    def raise_config_error():
        raise LLMConfigurationError("未配置 OPENAI_API_KEY，无法生成候选人画像。")

    monkeypatch.setattr(resumes, "build_resume_analyzer", raise_config_error)

    response = client.post(
        "/api/resumes/analyze",
        files={"file": ("resume.txt", "张晨".encode(), "text/plain")},
    )

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
