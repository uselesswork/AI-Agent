"""对不可变草稿版本的单行人工来源关联。"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.candidate import StrictModel

DocumentKind = Literal["resume", "letter"]
SourceKind = Literal["resume", "job"]


class AnnotationWrite(StrictModel):
    document: DocumentKind
    section_index: int = Field(ge=0)
    line_index: int = Field(ge=0)
    source_kind: SourceKind
    source_quote: str = Field(min_length=8, max_length=1000)
    note: str = Field(default="", max_length=500)


class AnnotationDetail(AnnotationWrite):
    id: int
    version_id: int
    application_id: int
    created_at: datetime
    updated_at: datetime
