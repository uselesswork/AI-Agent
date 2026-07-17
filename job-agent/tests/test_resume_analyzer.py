import asyncio
from typing import Any

import pytest

from app.services.llm import LLMResponseError
from app.services.resume_analyzer import ResumeAnalyzer


class FakeGenerator:
    provider = "openai"
    model = "gpt-test"

    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.system_prompt = ""
        self.user_prompt = ""

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.result


def test_resume_analyzer_builds_profile_and_includes_source_text() -> None:
    generator = FakeGenerator(
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

    profile = asyncio.run(ResumeAnalyzer(generator).analyze("张晨\nPython 后端开发实习生"))

    assert profile.basic_info.name == "张晨"
    assert "张晨\nPython 后端开发实习生" in generator.user_prompt
    assert "合法 JSON" in generator.system_prompt


def test_resume_analyzer_rejects_invalid_profile() -> None:
    generator = FakeGenerator({"skills": [{"name": "Python", "category": "未知"}]})

    with pytest.raises(LLMResponseError, match="不符合候选人画像结构"):
        asyncio.run(ResumeAnalyzer(generator).analyze("Python"))
