"""投递日程、站内提醒和基于已确认材料的面试准备。"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, field_validator

from app.models.candidate import StrictModel

MilestoneKind = Literal["deadline", "interview", "follow_up"]
ReminderState = Literal["overdue", "soon", "later", "completed"]


class MilestoneCreate(StrictModel):
    kind: MilestoneKind
    title: str = Field(min_length=1, max_length=200)
    scheduled_at: datetime
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("日程标题不能为空。")
        return value.strip()

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("日程时间必须包含时区；网页端会自动转换为 UTC。")
        return value.astimezone(UTC)


class MilestoneUpdate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    scheduled_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)
    completed: bool | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("日程标题不能为空。")
        return value.strip() if value is not None else None

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("日程时间必须包含时区。")
        return value.astimezone(UTC)


class MilestoneDetail(StrictModel):
    id: int
    application_id: int
    kind: MilestoneKind
    title: str
    scheduled_at: datetime
    notes: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    reminder_state: ReminderState
    application_title: str | None = None
    company: str | None = None


class ReminderList(StrictModel):
    items: list[MilestoneDetail]
    truncated: bool
    days: int


class PreparationPrompt(StrictModel):
    question: str
    focus: str
    reviewed_material_lines: list[str] = Field(default_factory=list)
    needs_example: bool


class InterviewPreparation(StrictModel):
    application_id: int
    version: int
    job_title: str | None
    company: str | None
    resume_title: str
    cover_letter_title: str
    prompts: list[PreparationPrompt]
    checklist: list[str]
    warning: str = "仅根据已人工确认版本与保存的岗位要求生成练习提纲；引用材料不代表事实已由系统核验，请用真实经历自行准备答案。"
