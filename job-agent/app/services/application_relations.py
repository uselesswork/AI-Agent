"""在同一事务内保存快照关联与状态事件。"""

import hashlib
import json

from sqlalchemy import insert, select

from app.core.database_schema import application_events, jobs, match_reports, resumes
from app.services.ownership import owned_ids, owner_key, register_owner


def attach_snapshot(connection, values: dict, source_key: str) -> dict:
    profile = values["candidate_profile"]
    fingerprint = hashlib.sha256(json.dumps(
        profile, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    fingerprint = owner_key(fingerprint)
    resume_id = connection.scalar(select(resumes.c.id).where(
        resumes.c.content_key == fingerprint, resumes.c.id.in_(owned_ids("resume"))))
    if resume_id is None:
        resume_id = connection.execute(insert(resumes).values(
            content_key=fingerprint, filename=values["resume_filename"],
            candidate_profile=profile, raw_text=None, created_at=values["created_at"],
        )).inserted_primary_key[0]
        register_owner(connection, "resume", resume_id)
    job_id = connection.scalar(select(jobs.c.id).where(
        jobs.c.source_key == source_key, jobs.c.id.in_(owned_ids("job"))))
    if job_id is None:
        job = values["job_profile"]
        job_id = connection.execute(insert(jobs).values(
            source_key=source_key, title=job.get("title"), company=job.get("company"),
            location=job.get("location"), raw_description=None, job_profile=job,
            job_url=values["job_url"], created_at=values["created_at"],
            updated_at=values["updated_at"],
        )).inserted_primary_key[0]
        register_owner(connection, "job", job_id)
    report_id = connection.scalar(select(match_reports.c.id).where(
        match_reports.c.source_key == source_key,
        match_reports.c.id.in_(owned_ids("report"))))
    if report_id is None:
        result = values["match_result"]
        report_id = connection.execute(insert(match_reports).values(
            source_key=source_key, resume_id=resume_id, job_id=job_id,
            overall_score=result["overall_score"], recommendation=result["recommendation"],
            result=result, provider=values["provider"], model=values["model"],
            created_at=values["created_at"],
        )).inserted_primary_key[0]
        register_owner(connection, "report", report_id)
    return {"resume_id": resume_id, "job_id": job_id, "match_report_id": report_id}


def add_event(connection, record_id, event_type, from_status, to_status, when, note):
    connection.execute(insert(application_events).values(
        application_id=record_id, event_type=event_type, from_status=from_status,
        to_status=to_status, occurred_at=when, note=note,
    ))
