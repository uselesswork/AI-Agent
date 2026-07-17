from typing import Literal

from pydantic import Field

from app.models.candidate import StrictModel


class JobRequirement(StrictModel):
    name: str
    category: Literal["技能", "学历", "经验", "时间", "地点", "其他"]
    importance: Literal["必须", "加分"]
    evidence: str = Field(description="岗位描述中的原文证据")


class JobProfile(StrictModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education: str | None = None
    experience: str | None = None
    internship_duration: str | None = None
    requirements: list[JobRequirement] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class JobParseRequest(StrictModel):
    description: str = Field(min_length=20, max_length=30000)
    provider: Literal["openai", "deepseek"] | None = None


class JobParseResponse(StrictModel):
    provider: Literal["openai", "deepseek"]
    model: str
    profile: JobProfile
