from datetime import datetime
from typing import Literal

from pydantic import model_validator

from app.models.candidate import StrictModel
from app.models.draft import DraftDocument


class DraftVersionCreate(StrictModel):
    resume: DraftDocument
    cover_letter: DraftDocument

    @model_validator(mode="after")
    def check_size(self) -> "DraftVersionCreate":
        documents = (self.resume, self.cover_letter)
        total = 0
        for document in documents:
            if not document.title.strip() or len(document.title) > 200:
                raise ValueError("文档标题须为 1～200 字符。")
            if not document.sections or len(document.sections) > 30:
                raise ValueError("每份文档须包含 1～30 个章节。")
            total += len(document.title)
            for section in document.sections:
                if not section.heading.strip() or len(section.heading) > 200:
                    raise ValueError("章节标题须为 1～200 字符。")
                if len(section.lines) > 100:
                    raise ValueError("每个章节最多 100 行。")
                total += len(section.heading)
                for line in section.lines:
                    if len(line) > 3000:
                        raise ValueError("单行内容最多 3000 字符。")
                    total += len(line)
        if total > 100_000:
            raise ValueError("两份文档合计最多 100000 字符。")
        return self


class DraftVersionSummary(StrictModel):
    id: int
    application_id: int
    version: int
    created_at: datetime
    reviewed_at: datetime | None


class DraftVersionDetail(DraftVersionSummary):
    resume: DraftDocument
    cover_letter: DraftDocument


class DraftReviewRequest(StrictModel):
    confirmed: Literal[True]
