from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator

from app.models.candidate import CandidateProfile, StrictModel
from app.models.job import JobProfile
from app.models.match import MatchResult


class ResumeAssetCreate(StrictModel):
    filename: str = Field(min_length=1, max_length=255)
    profile: CandidateProfile


class ResumeAsset(StrictModel):
    id: int
    filename: str
    profile: CandidateProfile
    created_at: datetime


class ResumeAssetSaved(StrictModel):
    asset: ResumeAsset
    created: bool


class JobAssetCreate(StrictModel):
    profile: JobProfile
    job_url: str | None = Field(default=None, max_length=2000)
    favorite: bool = False

    @field_validator("job_url")
    @classmethod
    def valid_job_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        parsed = urlsplit(value.strip())
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise ValueError("岗位链接必须是有效的 http 或 https 地址。")
        return value.strip()


class JobAsset(StrictModel):
    id: int
    profile: JobProfile
    job_url: str | None
    favorite: bool
    created_at: datetime


class JobAssetSaved(StrictModel):
    asset: JobAsset
    created: bool


class FavoriteUpdate(StrictModel):
    favorite: bool


class MatchReanalyzeRequest(StrictModel):
    resume_id: int = Field(ge=1)
    job_id: int = Field(ge=1)
    provider: Literal["openai", "deepseek"] | None = None


class ReportSummary(StrictModel):
    id: int
    resume_id: int
    job_id: int
    resume_filename: str
    job_title: str | None
    company: str | None
    overall_score: int
    recommendation: str
    provider: str
    model: str
    created_at: datetime


class ReportDetail(ReportSummary):
    result: MatchResult
