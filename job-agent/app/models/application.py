from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

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
    retain_source_text: bool = Field(default=False, exclude=True)
    resume_text: str | None = Field(default=None, max_length=1_000_000, exclude=True)
    job_description: str | None = Field(default=None, max_length=30_000, exclude=True)

    @model_validator(mode="after")
    def validate_source_consent(self) -> "ApplicationCreate":
        if self.retain_source_text:
            if not self.resume_text or not self.resume_text.strip():
                raise ValueError("同意留存原文时，必须提供已解析的简历正文。")
            if not self.job_description or not self.job_description.strip():
                raise ValueError("同意留存原文时，必须提供岗位描述。")
        elif self.resume_text is not None or self.job_description is not None:
            raise ValueError("提交原文前必须明确同意留存。")
        return self


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
