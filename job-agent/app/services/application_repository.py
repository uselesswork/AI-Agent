from __future__ import annotations

from datetime import UTC, datetime, time
from uuid import uuid4

from sqlalchemy import create_engine, delete, func, insert, or_, select, update
from sqlalchemy.engine import Engine, RowMapping

from app.core.database_schema import (
    application_events, application_sources, applications_table, draft_annotations, jobs,
    match_reports, metadata,
)
from app.services.application_relations import add_event, attach_snapshot
from app.services.ownership import is_owned, owned_ids, register_owner, remove_owner
from app.models.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationEvent,
    ApplicationPage,
    ApplicationStatus,
    ApplicationSummary,
    ApplicationUpdate,
)


class ApplicationNotFoundError(LookupError):
    """投递记录不存在。"""


class ApplicationRepository:
    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)
        # 临时 SQLite 测试库自动建表；真实 MySQL 只允许显式升级脚本修改结构。
        if self.engine.dialect.name == "sqlite":
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
            register_owner(connection, "application", record_id)
            if data.retain_source_text:
                connection.execute(insert(application_sources).values(
                    application_id=record_id, resume_text=data.resume_text,
                    job_description=data.job_description, stored_at=now,
                ))
            add_event(connection, record_id, "created", None, data.status, now, "创建投递记录")
        return self.get(record_id)

    def get_source_status(self, record_id: int) -> bool:
        with self.engine.connect() as connection:
            exists = is_owned(connection, "application", record_id)
            if not exists:
                raise ApplicationNotFoundError
            source = connection.scalar(select(application_sources.c.application_id).where(
                application_sources.c.application_id == record_id))
        return source is not None

    def get_sources(self, record_id: int) -> tuple[str, str] | None:
        with self.engine.connect() as connection:
            if not is_owned(connection, "application", record_id):
                raise ApplicationNotFoundError
            row = connection.execute(select(application_sources.c.resume_text,
                                            application_sources.c.job_description).where(
                application_sources.c.application_id == record_id)).first()
        return (row.resume_text, row.job_description) if row else None

    def delete_sources(self, record_id: int) -> None:
        with self.engine.begin() as connection:
            exists = is_owned(connection, "application", record_id)
            if not exists:
                raise ApplicationNotFoundError
            connection.execute(delete(draft_annotations).where(
                draft_annotations.c.application_id == record_id))
            connection.execute(delete(application_sources).where(
                application_sources.c.application_id == record_id))

    def list(
        self,
        status: ApplicationStatus | None = None,
        sort: str = "updated_desc",
    ) -> list[ApplicationSummary]:
        statement = select(applications_table).where(
            applications_table.c.id.in_(owned_ids("application")))
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

    def search(
        self, q: str = "", status: ApplicationStatus | None = None,
        sort: str = "updated_desc", page: int = 1, page_size: int = 10,
    ) -> ApplicationPage:
        """在数据库中筛选、排序和分页；旧快照缺少关联时回退到 JSON 字段。"""
        source = applications_table.outerjoin(jobs, applications_table.c.job_id == jobs.c.id)
        source = source.outerjoin(
            match_reports, applications_table.c.match_report_id == match_reports.c.id,
        )
        statement = select(applications_table).select_from(source).where(
            applications_table.c.id.in_(owned_ids("application")))
        if status:
            statement = statement.where(applications_table.c.status == status)
        if q:
            needle = q.lower()
            searchable = [
                func.coalesce(jobs.c.title, applications_table.c.job_profile["title"].as_string()),
                func.coalesce(jobs.c.company, applications_table.c.job_profile["company"].as_string()),
                func.coalesce(jobs.c.location, applications_table.c.job_profile["location"].as_string()),
                applications_table.c.notes,
            ]
            statement = statement.where(or_(*(
                func.lower(column).contains(needle, autoescape=True) for column in searchable
            )))
        score = func.coalesce(
            match_reports.c.overall_score,
            applications_table.c.match_result["overall_score"].as_integer(),
        )
        if sort == "score_desc":
            statement = statement.order_by(score.desc(), applications_table.c.id.desc())
        elif sort == "score_asc":
            statement = statement.order_by(score.asc(), applications_table.c.id.desc())
        else:
            statement = statement.order_by(
                applications_table.c.updated_at.desc(), applications_table.c.id.desc(),
            )
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        with self.engine.connect() as connection:
            total = connection.scalar(count_statement) or 0
            rows = connection.execute(
                statement.limit(page_size).offset((page - 1) * page_size)
            ).mappings().all()
        return ApplicationPage(items=[self._summary(row) for row in rows], total=total,
                               page=page, page_size=page_size)

    def list_events(self, record_id: int) -> list[ApplicationEvent]:
        with self.engine.connect() as connection:
            exists = is_owned(connection, "application", record_id)
            if not exists:
                raise ApplicationNotFoundError
            rows = connection.execute(select(application_events).where(
                application_events.c.application_id == record_id,
            ).order_by(application_events.c.occurred_at.desc(),
                       application_events.c.id.desc())).mappings().all()
        return [ApplicationEvent.model_validate(row) for row in rows]

    def get(self, record_id: int) -> ApplicationDetail:
        statement = select(applications_table).where(
            applications_table.c.id == record_id,
            applications_table.c.id.in_(owned_ids("application")))
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
        if "applied_at" in changes and changes["applied_at"] is not None:
            changes["applied_at"] = datetime.combine(changes["applied_at"], time.min)
        changes["updated_at"] = datetime.now(UTC)
        with self.engine.begin() as connection:
            old = connection.execute(select(applications_table).where(
                applications_table.c.id == record_id,
                applications_table.c.id.in_(owned_ids("application"))
            ).with_for_update()).mappings().first()
            if old is None:
                raise ApplicationNotFoundError
            target = changes.get("status", old["status"])
            if ("applied_at" not in changes and target == "已投递"
                    and old["status"] != "已投递" and old["applied_at"] is None):
                changes["applied_at"] = changes["updated_at"]
            connection.execute(update(applications_table).where(
                applications_table.c.id == record_id).values(**changes))
            if target != old["status"]:
                add_event(connection, record_id, "status_changed", old["status"], target,
                          changes["updated_at"], "通过看板修改状态")
            old_date = old["applied_at"].date() if old["applied_at"] else None
            new_date = changes["applied_at"].date() if changes.get("applied_at") else None
            if "applied_at" in data.model_fields_set and new_date != old_date:
                add_event(connection, record_id, "applied_at_changed", old["status"], target,
                          changes["updated_at"], "更新投递日期")
            if "job_url" in changes and old["job_id"] is not None and is_owned(
                    connection, "job", old["job_id"]):
                connection.execute(update(jobs).where(jobs.c.id == old["job_id"]).values(
                    job_url=changes["job_url"], updated_at=changes["updated_at"]))
        return self.get(record_id)

    def delete(self, record_id: int) -> None:
        statement = delete(applications_table).where(
            applications_table.c.id == record_id,
            applications_table.c.id.in_(owned_ids("application")))
        with self.engine.begin() as connection:
            result = connection.execute(statement)
            if result.rowcount:
                remove_owner(connection, "application", record_id)
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
            "applied_at": row["applied_at"].date() if row["applied_at"] else None,
        }
