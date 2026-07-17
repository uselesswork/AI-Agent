from typing import Literal

from pydantic import Field, model_validator

from app.models.candidate import CandidateProfile, StrictModel
from app.models.job import JobProfile


class ScoreDimension(StrictModel):
    name: Literal["技能匹配", "项目经验", "教育背景", "实习经历", "基本条件"]
    score: int = Field(ge=0, le=100)
    weight: int = Field(ge=0, le=100)
    reason: str


class RequirementAssessment(StrictModel):
    requirement: str
    status: Literal["满足", "部分满足", "不满足", "无法确认"]
    reason: str
    resume_evidence: list[str] = Field(default_factory=list)
    job_evidence: str | None = None


class MatchResult(StrictModel):
    overall_score: int = Field(ge=0, le=100)
    recommendation: Literal["建议投递", "谨慎投递", "暂不建议投递"]
    summary: str
    dimensions: list[ScoreDimension]
    assessments: list[RequirementAssessment] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    resume_suggestions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dimensions(self) -> "MatchResult":
        expected = {"技能匹配", "项目经验", "教育背景", "实习经历", "基本条件"}
        names = {item.name for item in self.dimensions}
        if names != expected or len(self.dimensions) != len(expected):
            raise ValueError("评分必须包含五个且不重复的维度")
        if sum(item.weight for item in self.dimensions) != 100:
            raise ValueError("评分维度权重之和必须为 100")
        return self


class MatchAnalyzeRequest(StrictModel):
    candidate_profile: CandidateProfile
    job_profile: JobProfile
    provider: Literal["openai", "deepseek"] | None = None


class MatchAnalyzeResponse(StrictModel):
    provider: Literal["openai", "deepseek"]
    model: str
    result: MatchResult
