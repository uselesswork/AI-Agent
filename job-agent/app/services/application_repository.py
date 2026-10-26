from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, delete, insert, select, update
from sqlalchemy.engine import Engine, RowMapping

from app.core.database_schema import application_sources, applications_table, jobs, metadata
from app.services.application_relations import add_event, attach_snapshot
from app.models.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationStatus,
    ApplicationSummary,
    ApplicationUpdate,
)


class ApplicationNotFoundError(LookupError):
    """投递记录不存在。"""


class ApplicationRepository:
    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)
        metadata.create_all(self.engine)

    def create(self, data: ApplicationCreate) -> ApplicationDetail:
        now = datetime.now(UTC)
        values = {
            "resume_filename": data.resume_filename,
            "candidate_profile": data.candidate_profile.model_dump(mode="json"),
            "job_profile": data.job_profile.model_dump(mode="json"),
            "match_result": data.match_result.model_dump(mode="json"),
            "provider": data.provider,
            "model": data.model,
            "status": data.status,
            "job_url": data.job_url,
            "notes": data.notes,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            values.update(attach_snapshot(connection, values, f"save:{uuid4().hex}"))
            if data.status == "已投递":
                values["applied_at"] = now
            result = connection.execute(insert(applications_table).values(**values))
            record_id = int(result.inserted_primary_key[0])
            if data.retain_source_text:
                connection.execute(insert(application_sources).values(
                    application_id=record_id, resume_text=data.resume_text,
                    job_description=data.job_description, stored_at=now,
                ))
            add_event(connection, record_id, "created", None, data.status, now, "创建投递记录")
        return self.get(record_id)

    def get_source_status(self, record_id: int) -> bool:
        with self.engine.connect() as connection:
            exists = connection.scalar(select(applications_table.c.id).where(
                applications_table.c.id == record_id))
            if exists is None:
                raise ApplicationNotFoundError
            source = connection.scalar(select(application_sources.c.application_id).where(
                application_sources.c.application_id == record_id))
        return source is not None

    def get_sources(self, record_id: int) -> tuple[str, str] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(application_sources.c.resume_text,
                                            application_sources.c.job_description).where(
                application_sources.c.application_id == record_id)).first()
        return (row.resume_text, row.job_description) if row else None

    def delete_sources(self, record_id: int) -> None:
        with self.engine.begin() as connection:
            exists = connection.scalar(select(applications_table.c.id).where(
                applications_table.c.id == record_id))
            if exists is None:
                raise ApplicationNotFoundError
            connection.execute(delete(application_sources).where(
                application_sources.c.application_id == record_id))

    def list(
        self,
        status: ApplicationStatus | None = None,
        sort: str = "updated_desc",
    ) -> list[ApplicationSummary]:
        statement = select(applications_table)
        if status:
            statement = statement.where(applications_table.c.status == status)
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        summaries = [self._summary(row) for row in rows]
        if sort == "score_desc":
            return sorted(summaries, key=lambda item: item.overall_score, reverse=True)
        if sort == "score_asc":
            return sorted(summaries, key=lambda item: item.overall_score)
        return sorted(summaries, key=lambda item: item.updated_at, reverse=True)

    def get(self, record_id: int) -> ApplicationDetail:
        statement = select(applications_table).where(applications_table.c.id == record_id)
        with self.engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        if row is None:
            raise ApplicationNotFoundError
        return ApplicationDetail.model_validate(
            {
                **self._summary_data(row),
                "resume_filename": row["resume_filename"],
                "candidate_profile": row["candidate_profile"],
                "job_profile": row["job_profile"],
                "match_result": row["match_result"],
                "provider": row["provider"],
                "model": row["model"],
            }
        )

    def update(self, record_id: int, data: ApplicationUpdate) -> ApplicationDetail:
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return self.get(record_id)
        changes["updated_at"] = datetime.now(UTC)
        with self.engine.begin() as connection:
            old = connection.execute(select(applications_table).where(
                applications_table.c.id == record_id).with_for_update()).mappings().first()
            if old is None:
                raise ApplicationNotFoundError
            target = changes.get("status", old["status"])
            if target == "已投递" and old["applied_at"] is None:
                changes["applied_at"] = changes["updated_at"]
            connection.execute(update(applications_table).where(
                applications_table.c.id == record_id).values(**changes))
            if target != old["status"]:
                add_event(connection, record_id, "status_changed", old["status"], target,
                          changes["updated_at"], "通过看板修改状态")
            if "job_url" in changes and old["job_id"] is not None:
                connection.execute(update(jobs).where(jobs.c.id == old["job_id"]).values(
                    job_url=changes["job_url"], updated_at=changes["updated_at"]))
        return self.get(record_id)

    def delete(self, record_id: int) -> None:
        statement = delete(applications_table).where(applications_table.c.id == record_id)
        with self.engine.begin() as connection:
            result = connection.execute(statement)
        if result.rowcount == 0:
            raise ApplicationNotFoundError

    def _summary(self, row: RowMapping) -> ApplicationSummary:
        return ApplicationSummary.model_validate(self._summary_data(row))

    @staticmethod
    def _summary_data(row: RowMapping) -> dict:
        job = row["job_profile"]
        match = row["match_result"]
        return {
            "id": row["id"],
            "company": job.get("company"),
            "title": job.get("title"),
            "location": job.get("location"),
            "overall_score": match["overall_score"],
            "recommendation": match["recommendation"],
            "status": row["status"],
            "job_url": row["job_url"],
            "notes": row["notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
