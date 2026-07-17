from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    quote: str = Field(description="简历中的原文证据，不得改写或虚构")
    source_section: str | None = Field(default=None, description="证据所在章节")


class BasicInfo(StrictModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = Field(default_factory=list)


class EducationEntry(StrictModel):
    institution: str
    degree: str | None = None
    major: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    courses: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class SkillItem(StrictModel):
    name: str
    category: Literal["编程语言", "框架", "数据库", "工程工具", "AI", "其他"]
    level: str | None = Field(default=None, description="仅在简历明确说明时填写")
    evidence: list[Evidence] = Field(default_factory=list)


class ProjectEntry(StrictModel):
    name: str
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class ExperienceEntry(StrictModel):
    organization: str
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    highlights: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class CertificateEntry(StrictModel):
    name: str
    date: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class CandidateProfile(StrictModel):
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    job_targets: list[str] = Field(default_factory=list)
    summary: str | None = None
    education: list[EducationEntry] = Field(default_factory=list)
    skills: list[SkillItem] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    experiences: list[ExperienceEntry] = Field(default_factory=list)
    certificates: list[CertificateEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ResumeAnalysisResponse(StrictModel):
    filename: str
    provider: Literal["openai", "deepseek"]
    model: str
    profile: CandidateProfile
