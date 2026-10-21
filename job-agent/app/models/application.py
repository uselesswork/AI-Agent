from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.models.candidate import CandidateProfile, StrictModel
from app.models.job import JobProfile
from app.models.match import MatchResult

ApplicationStatus = Literal["待投递", "已投递", "笔试", "面试", "Offer", "已拒绝"]


class ApplicationCreate(StrictModel):
    resume_filename: str = Field(min_length=1, max_length=255)
    candidate_profile: CandidateProfile
    job_profile: JobProfile
    match_result: MatchResult
    provider: Literal["openai", "deepseek"]
    model: str = Field(min_length=1, max_length=255)
    status: ApplicationStatus = "待投递"
    job_url: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=5000)


class ApplicationUpdate(StrictModel):
    status: ApplicationStatus | None = None
    job_url: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def status_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("状态不能设为空值；无需修改时请省略该字段。")
        return value


class ApplicationSummary(StrictModel):
    id: int
    company: str | None
    title: str | None
    location: str | None
    overall_score: int
    recommendation: str
    status: ApplicationStatus
    job_url: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationSummary):
    resume_filename: str
    candidate_profile: CandidateProfile
    job_profile: JobProfile
    match_result: MatchResult
    provider: Literal["openai", "deepseek"]
    model: str
