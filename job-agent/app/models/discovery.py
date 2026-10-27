from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.models.candidate import StrictModel

SourceName = Literal["greenhouse", "lever"]
BOARD_PATTERN = r"^[A-Za-z0-9_-]{1,80}$"
POSTING_PATTERN = r"^[A-Za-z0-9_-]{1,100}$"


class DiscoverySearch(StrictModel):
    source: SourceName
    board_token: str = Field(pattern=BOARD_PATTERN)
    keyword: str = Field(default="", max_length=100)
    location: str = Field(default="", max_length=100)
    internship_only: bool = False

    @field_validator("board_token")
    @classmethod
    def normalize_board(cls, value: str) -> str:
        return value.lower()


class PostingPreview(StrictModel):
    source: SourceName
    board_token: str
    external_id: str
    title: str
    company: str | None
    location: str | None
    commitment: str | None
    job_url: str
    description_excerpt: str
    imported_job_id: int | None = None


class DiscoveryResults(StrictModel):
    items: list[PostingPreview]
    scanned: int
    truncated: bool


class ImportRequest(StrictModel):
    source: SourceName
    board_token: str = Field(pattern=BOARD_PATTERN)
    external_id: str = Field(pattern=POSTING_PATTERN)
    llm_provider: Literal["openai", "deepseek"] | None = None

    @field_validator("board_token")
    @classmethod
    def normalize_board(cls, value: str) -> str:
        return value.lower()


class ImportRecord(StrictModel):
    id: int
    job_id: int
    source: SourceName
    board_token: str
    external_id: str
    source_url: str
    title: str | None
    company: str | None
    location: str | None
    imported_at: datetime


class ImportResult(StrictModel):
    record: ImportRecord
    created: bool
    job_reused: bool
