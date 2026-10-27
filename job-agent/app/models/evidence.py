from typing import Literal

from pydantic import Field

from app.models.candidate import StrictModel
from app.models.annotation import AnnotationDetail


class SourceStatus(StrictModel):
    retained: bool


class EvidenceLine(StrictModel):
    document: Literal["resume", "letter"]
    section_index: int
    line_index: int
    section: str
    line_number: int
    text: str
    source: Literal["resume", "job"] | None = None
    source_excerpt: str | None = None
    source_offset: int | None = None
    annotation: AnnotationDetail | None = None
    attention: Literal["literal_only", "review", "job_as_resume"]
    attention_reason: str


class EvidenceReport(StrictModel):
    application_id: int
    version: int
    lines: list[EvidenceLine] = Field(default_factory=list)
    resume_hits: int
    job_hits: int
    unmatched: int
    job_as_resume: int = 0
    warning: str = "只检查字面片段是否出现在留存原文；命中不证明表述真实，未命中也不等于虚构。"


class VersionComparison(StrictModel):
    application_id: int
    from_version: int
    to_version: int
    resume_diff: list[str] = Field(default_factory=list)
    cover_letter_diff: list[str] = Field(default_factory=list)
