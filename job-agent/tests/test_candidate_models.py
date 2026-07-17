import pytest
from pydantic import ValidationError

from app.models.candidate import CandidateProfile


def test_candidate_profile_accepts_evidence_based_data() -> None:
    profile = CandidateProfile.model_validate(
        {
            "basic_info": {"name": "张晨", "links": []},
            "job_targets": ["Python 后端开发实习生"],
            "skills": [
                {
                    "name": "FastAPI",
                    "category": "框架",
                    "level": None,
                    "evidence": [{"quote": "使用 FastAPI 构建简历上传接口"}],
                }
            ],
        }
    )

    assert profile.basic_info.name == "张晨"
    assert profile.skills[0].evidence[0].quote == "使用 FastAPI 构建简历上传接口"


def test_candidate_profile_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        CandidateProfile.model_validate({"invented_field": "不允许"})
