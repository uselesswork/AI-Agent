from typing import Literal

from pydantic import Field

from app.models.candidate import StrictModel


class SourceStatus(StrictModel):
    retained: bool


class EvidenceLine(StrictModel):
    document: Literal["resume", "letter"]
    section: str
    line_number: int
    text: str
    source: Literal["resume", "job"] | None = None
    source_excerpt: str | None = None
    source_offset: int | None = None


class EvidenceReport(StrictModel):
    application_id: int
    version: int
    lines: list[EvidenceLine] = Field(default_factory=list)
    resume_hits: int
    job_hits: int
    unmatched: int
    warning: str = "只检查字面片段是否出现在留存原文；命中不证明表述真实，未命中也不等于虚构。"


class VersionComparison(StrictModel):
    application_id: int
    from_version: int
    to_version: int
    resume_diff: list[str] = Field(default_factory=list)
    cover_letter_diff: list[str] = Field(default_factory=list)
