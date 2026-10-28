from datetime import UTC, datetime

from sqlalchemy import func, insert, select, update
from sqlalchemy.engine import Engine, RowMapping

from app.core.database_schema import applications_table, draft_versions
from app.models.draft_version import (
    DraftVersionCreate, DraftVersionDetail, DraftVersionSummary,
)
from app.services.application_repository import ApplicationNotFoundError
from app.services.ownership import owned_ids


class DraftVersionNotFoundError(LookupError):
    """草稿版本不存在或不属于指定投递。"""


class DraftVersionRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, application_id: int, data: DraftVersionCreate) -> DraftVersionDetail:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            # MySQL 按投递记录加锁，串行分配该记录的版本号。
            application = connection.execute(select(applications_table.c.id).where(
                applications_table.c.id == application_id,
                applications_table.c.id.in_(owned_ids("application"))).with_for_update()).first()
            if application is None:
                raise ApplicationNotFoundError
            last = connection.scalar(select(func.max(draft_versions.c.version)).where(
                draft_versions.c.application_id == application_id)) or 0
            result = connection.execute(insert(draft_versions).values(
                application_id=application_id,
                version=last + 1,
                resume=data.resume.model_dump(mode="json"),
                cover_letter=data.cover_letter.model_dump(mode="json"),
                created_at=now,
            ))
            row_id = int(result.inserted_primary_key[0])
        return self.get_by_id(row_id)

    def list(self, application_id: int) -> list[DraftVersionSummary]:
        with self.engine.connect() as connection:
            exists = connection.scalar(select(applications_table.c.id).where(
                applications_table.c.id == application_id,
                applications_table.c.id.in_(owned_ids("application"))))
            if exists is None:
                raise ApplicationNotFoundError
            rows = connection.execute(select(
                draft_versions.c.id, draft_versions.c.application_id,
                draft_versions.c.version, draft_versions.c.created_at,
                draft_versions.c.reviewed_at,
            ).where(
                draft_versions.c.application_id == application_id).order_by(
                    draft_versions.c.version.desc())).mappings().all()
        return [DraftVersionSummary.model_validate(row) for row in rows]

    def get(self, application_id: int, version: int) -> DraftVersionDetail:
        with self.engine.connect() as connection:
            row = connection.execute(select(draft_versions).where(
                draft_versions.c.application_id == application_id,
                draft_versions.c.application_id.in_(owned_ids("application")),
                draft_versions.c.version == version)).mappings().first()
        if row is None:
            raise DraftVersionNotFoundError
        return self._detail(row)

    def get_by_id(self, row_id: int) -> DraftVersionDetail:
        with self.engine.connect() as connection:
            row = connection.execute(select(draft_versions).where(
                draft_versions.c.id == row_id,
                draft_versions.c.application_id.in_(owned_ids("application")))).mappings().one()
        return self._detail(row)

    def confirm(self, application_id: int, version: int) -> DraftVersionDetail:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            row = connection.execute(select(draft_versions).where(
                draft_versions.c.application_id == application_id,
                draft_versions.c.application_id.in_(owned_ids("application")),
                draft_versions.c.version == version).with_for_update()).mappings().first()
            if row is None:
                raise DraftVersionNotFoundError
            if row["reviewed_at"] is None:
                connection.execute(update(draft_versions).where(
                    draft_versions.c.id == row["id"]).values(reviewed_at=now))
        return self.get(application_id, version)

    @staticmethod
    def _detail(row: RowMapping) -> DraftVersionDetail:
        return DraftVersionDetail.model_validate(row)
