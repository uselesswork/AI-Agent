from typing import Literal

from pydantic import Field

from app.models.candidate import StrictModel

DraftTemplate = Literal["standard", "compact"]


class DraftSection(StrictModel):
    heading: str
    lines: list[str] = Field(default_factory=list)


class DraftDocument(StrictModel):
    title: str
    sections: list[DraftSection] = Field(default_factory=list)


class ApplicationDraft(StrictModel):
    template: DraftTemplate = "standard"
    resume: DraftDocument
    cover_letter: DraftDocument
    suggestions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
