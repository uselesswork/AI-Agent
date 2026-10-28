"""投递日程持久化；提醒由时间实时计算，不建立后台通知任务。"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Engine, RowMapping

from app.core.database_schema import application_milestones, applications_table, jobs
from app.models.planning import (
    MilestoneCreate, MilestoneDetail, MilestoneUpdate, ReminderList, ReminderState,
)
from app.services.application_repository import ApplicationNotFoundError
from app.services.ownership import owned_ids


class MilestoneNotFoundError(LookupError):
    """日程不存在或不属于该投递。"""


def _db_time(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(tzinfo=None)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class PlanningRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def _statement():
        return select(
            application_milestones,
            jobs.c.title.label("application_title"), jobs.c.company,
        ).select_from(application_milestones.join(
            applications_table,
            application_milestones.c.application_id == applications_table.c.id,
        ).outerjoin(jobs, applications_table.c.job_id == jobs.c.id))

    @staticmethod
    def _detail(row: RowMapping, now: datetime, days: int = 7) -> MilestoneDetail:
        scheduled = _utc(row["scheduled_at"])
        completed = _utc(row["completed_at"])
        state: ReminderState = (
            "completed" if completed else "overdue" if scheduled < now else
            "soon" if scheduled <= now + timedelta(days=days) else "later"
        )
        return MilestoneDetail(
            id=row["id"], application_id=row["application_id"], kind=row["kind"],
            title=row["title"], scheduled_at=scheduled, notes=row["notes"],
            completed_at=completed, created_at=_utc(row["created_at"]),
            updated_at=_utc(row["updated_at"]), reminder_state=state,
            application_title=row["application_title"], company=row["company"],
        )

    def _ensure_application(self, connection, application_id: int) -> None:
        exists = connection.scalar(select(applications_table.c.id).where(
            applications_table.c.id == application_id,
            applications_table.c.id.in_(owned_ids("application"))))
        if exists is None:
            raise ApplicationNotFoundError

    def create(self, application_id: int, data: MilestoneCreate) -> MilestoneDetail:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            self._ensure_application(connection, application_id)
            result = connection.execute(insert(application_milestones).values(
                application_id=application_id, kind=data.kind, title=data.title,
                scheduled_at=_db_time(data.scheduled_at), notes=data.notes,
                created_at=_db_time(now), updated_at=_db_time(now),
            ))
            milestone_id = int(result.inserted_primary_key[0])
        return self.get(application_id, milestone_id)

    def get(self, application_id: int, milestone_id: int) -> MilestoneDetail:
        with self.engine.connect() as connection:
            row = connection.execute(self._statement().where(
                application_milestones.c.application_id == application_id,
                application_milestones.c.application_id.in_(owned_ids("application")),
                application_milestones.c.id == milestone_id,
            )).mappings().first()
        if row is None:
            raise MilestoneNotFoundError
        return self._detail(row, datetime.now(UTC))

    def list(self, application_id: int) -> list[MilestoneDetail]:
        with self.engine.connect() as connection:
            self._ensure_application(connection, application_id)
            rows = connection.execute(self._statement().where(
                application_milestones.c.application_id == application_id,
            ).order_by(application_milestones.c.scheduled_at,
                       application_milestones.c.id)).mappings().all()
        now = datetime.now(UTC)
        return [self._detail(row, now) for row in rows]

    def update(self, application_id: int, milestone_id: int,
               data: MilestoneUpdate) -> MilestoneDetail:
        values = data.model_dump(exclude_unset=True)
        if not values or any(values.get(key) is None for key in ("title", "scheduled_at")
                             if key in values) or values.get("completed", True) is None:
            raise ValueError("请提交至少一项有效修改，标题、时间和完成状态不能设为空。")
        now = datetime.now(UTC)
        if "scheduled_at" in values:
            values["scheduled_at"] = _db_time(values["scheduled_at"])
        completed = values.pop("completed", None)
        values["updated_at"] = _db_time(now)
        with self.engine.begin() as connection:
            row = connection.execute(select(
                application_milestones.c.id, application_milestones.c.completed_at,
            ).where(
                application_milestones.c.id == milestone_id,
                application_milestones.c.application_id == application_id,
                application_milestones.c.application_id.in_(owned_ids("application")),
            ).with_for_update()).first()
            if row is None:
                raise MilestoneNotFoundError
            if completed is not None:
                values["completed_at"] = (row.completed_at or _db_time(now)) if completed else None
            connection.execute(update(application_milestones).where(
                application_milestones.c.id == milestone_id).values(**values))
        return self.get(application_id, milestone_id)

    def delete(self, application_id: int, milestone_id: int) -> None:
        with self.engine.begin() as connection:
            result = connection.execute(delete(application_milestones).where(
                application_milestones.c.id == milestone_id,
                application_milestones.c.application_id == application_id,
                application_milestones.c.application_id.in_(owned_ids("application")),
            ))
            if result.rowcount == 0:
                raise MilestoneNotFoundError

    def reminders(self, days: int) -> ReminderList:
        now = datetime.now(UTC)
        cutoff = _db_time(now + timedelta(days=days))
        with self.engine.connect() as connection:
            rows = connection.execute(self._statement().where(
                application_milestones.c.completed_at.is_(None),
                application_milestones.c.scheduled_at <= cutoff,
                application_milestones.c.application_id.in_(owned_ids("application")),
            ).order_by(application_milestones.c.scheduled_at,
                       application_milestones.c.id).limit(101)).mappings().all()
        return ReminderList(items=[self._detail(row, now, days) for row in rows[:100]],
                            truncated=len(rows) > 100, days=days)
