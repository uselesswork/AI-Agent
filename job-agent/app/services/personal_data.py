"""只导出/删除当前账号拥有的关系数据，不包含密码哈希、会话或环境密钥。"""

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from app.core.database_schema import (
    application_events, application_milestones, application_sources, applications_table,
    auth_sessions,
    draft_annotations, draft_versions, job_favorites, job_imports, jobs, match_reports,
    resumes, user_assets, users,
)


def _owned_ids(connection, user_id: int, kind: str) -> list[int]:
    return list(connection.scalars(select(user_assets.c.entity_id).where(
        user_assets.c.user_id == user_id, user_assets.c.entity_type == kind,
    )))


def export_personal_data(engine: Engine, user_id: int) -> dict:
    with engine.connect() as connection:
        username = connection.scalar(select(users.c.username).where(users.c.id == user_id))
        if username is None:
            raise ValueError("账号不存在。")
        ids = {kind: _owned_ids(connection, user_id, kind)
               for kind in ("resume", "job", "report", "application")}

        def rows(table, predicate) -> list[dict]:
            return [dict(row) for row in connection.execute(select(table).where(
                predicate)).mappings().all()]

        data = {
            "resumes": rows(resumes, resumes.c.id.in_(ids["resume"])),
            "jobs": rows(jobs, jobs.c.id.in_(ids["job"])),
            "match_reports": rows(match_reports, match_reports.c.id.in_(ids["report"])),
            "applications": rows(applications_table,
                                 applications_table.c.id.in_(ids["application"])),
            "application_events": rows(application_events,
                                       application_events.c.application_id.in_(ids["application"])),
            "draft_versions": rows(draft_versions,
                                   draft_versions.c.application_id.in_(ids["application"])),
            "application_sources": rows(application_sources,
                                        application_sources.c.application_id.in_(ids["application"])),
            "draft_annotations": rows(draft_annotations,
                                      draft_annotations.c.application_id.in_(ids["application"])),
            "application_milestones": rows(application_milestones,
                                          application_milestones.c.application_id.in_(ids["application"])),
            "job_favorites": rows(job_favorites,
                                  job_favorites.c.job_id.in_(ids["job"])),
            "job_imports": rows(job_imports, job_imports.c.user_id == user_id),
        }
    return {"username": username, "exported_at": datetime.now(UTC), "data": data}


def delete_personal_data(engine: Engine, user_id: int) -> None:
    with engine.begin() as connection:
        exists = connection.scalar(select(users.c.id).where(
            users.c.id == user_id).with_for_update())
        if exists is None:
            raise ValueError("账号不存在。")
        ids = {kind: _owned_ids(connection, user_id, kind)
               for kind in ("resume", "job", "report", "application")}
        connection.execute(delete(draft_annotations).where(
            draft_annotations.c.application_id.in_(ids["application"])))
        connection.execute(delete(application_sources).where(
            application_sources.c.application_id.in_(ids["application"])))
        connection.execute(delete(draft_versions).where(
            draft_versions.c.application_id.in_(ids["application"])))
        connection.execute(delete(application_events).where(
            application_events.c.application_id.in_(ids["application"])))
        connection.execute(delete(application_milestones).where(
            application_milestones.c.application_id.in_(ids["application"])))
        connection.execute(delete(job_favorites).where(
            job_favorites.c.job_id.in_(ids["job"])))
        connection.execute(delete(job_imports).where(job_imports.c.user_id == user_id))
        connection.execute(delete(applications_table).where(
            applications_table.c.id.in_(ids["application"])))
        connection.execute(delete(match_reports).where(
            match_reports.c.id.in_(ids["report"])))
        connection.execute(delete(jobs).where(jobs.c.id.in_(ids["job"])))
        connection.execute(delete(resumes).where(resumes.c.id.in_(ids["resume"])))
        connection.execute(delete(user_assets).where(user_assets.c.user_id == user_id))
        connection.execute(delete(auth_sessions).where(auth_sessions.c.user_id == user_id))
        connection.execute(delete(users).where(users.c.id == user_id))
