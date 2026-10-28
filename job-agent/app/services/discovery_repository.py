"""公开职位导入来源记录；不存储外部接口原始响应。"""

from datetime import UTC, datetime

from sqlalchemy import insert, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.core.database_schema import job_imports, jobs
from app.core.user_scope import current_user_id
from app.models.discovery import ImportRecord, SourceName
from app.services.ownership import is_owned


class DiscoveryRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def _statement():
        return select(
            job_imports.c.id, job_imports.c.job_id, job_imports.c.source,
            job_imports.c.board_token, job_imports.c.external_id,
            job_imports.c.source_url, job_imports.c.imported_at,
            jobs.c.title, jobs.c.company, jobs.c.location,
        ).select_from(job_imports.join(jobs, job_imports.c.job_id == jobs.c.id))

    def get(self, source: SourceName, board: str, external_id: str) -> ImportRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(self._statement().where(
                job_imports.c.user_id == current_user_id(),
                job_imports.c.source == source, job_imports.c.board_token == board,
                job_imports.c.external_id == external_id,
            )).mappings().first()
        return ImportRecord.model_validate(row) if row else None

    def imported_ids(self, source: SourceName, board: str) -> dict[str, int]:
        with self.engine.connect() as connection:
            rows = connection.execute(select(job_imports.c.external_id, job_imports.c.job_id).where(
                job_imports.c.user_id == current_user_id(),
                job_imports.c.source == source, job_imports.c.board_token == board,
            )).all()
        return {row.external_id: row.job_id for row in rows}

    def list(self) -> list[ImportRecord]:
        with self.engine.connect() as connection:
            rows = connection.execute(self._statement().order_by(
                job_imports.c.imported_at.desc(), job_imports.c.id.desc(),
            ).where(job_imports.c.user_id == current_user_id()).limit(100)).mappings().all()
        return [ImportRecord.model_validate(row) for row in rows]

    def create(self, source: SourceName, board: str, external_id: str,
               job_id: int, source_url: str) -> tuple[ImportRecord, bool]:
        existing = self.get(source, board, external_id)
        if existing is not None:
            return existing, False
        try:
            with self.engine.begin() as connection:
                if not is_owned(connection, "job", job_id):
                    raise ValueError("岗位不属于当前用户。")
                connection.execute(insert(job_imports).values(
                    job_id=job_id, user_id=current_user_id(), source=source, board_token=board,
                    external_id=external_id, source_url=source_url,
                    imported_at=datetime.now(UTC),
                ))
        except IntegrityError:
            existing = self.get(source, board, external_id)
            if existing is None:
                raise
            return existing, False
        return self.get(source, board, external_id), True
