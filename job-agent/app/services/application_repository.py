from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, MetaData, String, Table, Text, create_engine
from sqlalchemy import Column, delete, insert, select, update
from sqlalchemy.engine import Engine, RowMapping

from app.models.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationStatus,
    ApplicationSummary,
    ApplicationUpdate,
)


class ApplicationNotFoundError(LookupError):
    """投递记录不存在。"""


metadata = MetaData()
applications_table = Table(
    "applications",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("resume_filename", String(255), nullable=False),
    Column("candidate_profile", JSON, nullable=False),
    Column("job_profile", JSON, nullable=False),
    Column("match_result", JSON, nullable=False),
    Column("provider", String(20), nullable=False),
    Column("model", String(255), nullable=False),
    Column("status", String(20), nullable=False, index=True),
    Column("job_url", String(2000)),
    Column("notes", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, index=True),
)


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
            result = connection.execute(insert(applications_table).values(**values))
            record_id = int(result.inserted_primary_key[0])
        return self.get(record_id)

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
        statement = (
            update(applications_table)
            .where(applications_table.c.id == record_id)
            .values(**changes)
        )
        with self.engine.begin() as connection:
            result = connection.execute(statement)
        if result.rowcount == 0:
            raise ApplicationNotFoundError
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
