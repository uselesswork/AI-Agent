"""独立画像、岗位和报告资料库；不保存上传文件字节或简历/JD 原文。"""

import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from sqlalchemy import delete, insert, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.core.database_schema import (
    applications_table, job_favorites, jobs, match_reports, resumes,
)
from app.models.library import (
    JobAsset, JobAssetCreate, JobAssetSaved, ReportDetail, ReportSummary,
    ResumeAsset, ResumeAssetCreate, ResumeAssetSaved,
)
from app.models.match import MatchResult


class AssetNotFoundError(LookupError):
    """资料或报告不存在。"""


class AssetInUseError(RuntimeError):
    """资料仍被报告或投递引用。"""


def _fingerprint(value: dict) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalized_url(url: str | None) -> str | None:
    if not url or not url.strip():
        return None
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("岗位链接必须是有效的 http 或 https 地址。")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(),
                       parsed.path.rstrip("/"), parsed.query, ""))


class LibraryRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save_resume(self, data: ResumeAssetCreate) -> ResumeAssetSaved:
        profile = data.profile.model_dump(mode="json")
        key = _fingerprint(profile)
        try:
            with self.engine.begin() as connection:
                record_id = connection.scalar(select(resumes.c.id).where(resumes.c.content_key == key))
                created = record_id is None
                if created:
                    record_id = connection.execute(insert(resumes).values(
                        content_key=key, filename=data.filename, raw_text=None,
                        candidate_profile=profile, created_at=datetime.now(UTC),
                    )).inserted_primary_key[0]
        except IntegrityError:
            with self.engine.connect() as connection:
                record_id = connection.scalar(select(resumes.c.id).where(resumes.c.content_key == key))
            if record_id is None:
                raise
            created = False
        return ResumeAssetSaved(asset=self.get_resume(int(record_id)), created=created)

    def list_resumes(self) -> list[ResumeAsset]:
        with self.engine.connect() as connection:
            rows = connection.execute(select(resumes).order_by(resumes.c.id.desc())).mappings().all()
        return [self._resume(row) for row in rows]

    def get_resume(self, record_id: int) -> ResumeAsset:
        with self.engine.connect() as connection:
            row = connection.execute(select(resumes).where(resumes.c.id == record_id)).mappings().first()
        if row is None:
            raise AssetNotFoundError
        return self._resume(row)

    def delete_resume(self, record_id: int) -> None:
        try:
            with self.engine.begin() as connection:
                if connection.scalar(select(resumes.c.id).where(resumes.c.id == record_id)) is None:
                    raise AssetNotFoundError
                if (connection.scalar(select(match_reports.c.id).where(
                        match_reports.c.resume_id == record_id).limit(1)) is not None
                        or connection.scalar(select(applications_table.c.id).where(
                            applications_table.c.resume_id == record_id).limit(1)) is not None):
                    raise AssetInUseError
                connection.execute(delete(resumes).where(resumes.c.id == record_id))
        except IntegrityError as exc:
            raise AssetInUseError from exc

    def save_job(self, data: JobAssetCreate) -> JobAssetSaved:
        profile = data.profile.model_dump(mode="json")
        url = _normalized_url(data.job_url)
        key_source = f"url:{url}" if url else f"profile:{_fingerprint(profile)}"
        key = f"library:{hashlib.sha256(key_source.encode('utf-8')).hexdigest()}"
        with self.engine.begin() as connection:
            rows = connection.execute(select(jobs.c.id, jobs.c.job_profile, jobs.c.job_url)).all()
            record_id = None
            for row in rows:
                if url:
                    try:
                        matches = _normalized_url(row.job_url) == url
                    except ValueError:
                        matches = False  # 旧记录可能保存了非 URL 文本。
                else:
                    matches = row.job_profile == profile
                if matches:
                    record_id = row.id
                    break
            created = record_id is None
            if created:
                record_id = connection.execute(insert(jobs).values(
                    source_key=key, title=profile.get("title"), company=profile.get("company"),
                    location=profile.get("location"), raw_description=None, job_profile=profile,
                    job_url=url, created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
                )).inserted_primary_key[0]
            if data.favorite and connection.scalar(select(job_favorites.c.job_id).where(
                    job_favorites.c.job_id == record_id)) is None:
                connection.execute(insert(job_favorites).values(
                    job_id=record_id, created_at=datetime.now(UTC),
                ))
        return JobAssetSaved(asset=self.get_job(int(record_id)), created=created)

    def list_jobs(self, favorite_only: bool = False) -> list[JobAsset]:
        source = jobs.outerjoin(job_favorites, jobs.c.id == job_favorites.c.job_id)
        statement = select(jobs, job_favorites.c.job_id.label("favorite_id")).select_from(source)
        if favorite_only:
            statement = statement.where(job_favorites.c.job_id.is_not(None))
        with self.engine.connect() as connection:
            rows = connection.execute(statement.order_by(jobs.c.id.desc())).mappings().all()
        return [self._job(row) for row in rows]

    def get_job(self, record_id: int) -> JobAsset:
        source = jobs.outerjoin(job_favorites, jobs.c.id == job_favorites.c.job_id)
        with self.engine.connect() as connection:
            row = connection.execute(select(jobs, job_favorites.c.job_id.label("favorite_id"))
                                     .select_from(source).where(jobs.c.id == record_id)).mappings().first()
        if row is None:
            raise AssetNotFoundError
        return self._job(row)

    def set_favorite(self, record_id: int, favorite: bool) -> JobAsset:
        with self.engine.begin() as connection:
            if connection.scalar(select(jobs.c.id).where(jobs.c.id == record_id)) is None:
                raise AssetNotFoundError
            old = connection.scalar(select(job_favorites.c.job_id).where(
                job_favorites.c.job_id == record_id))
            if favorite and old is None:
                connection.execute(insert(job_favorites).values(
                    job_id=record_id, created_at=datetime.now(UTC),
                ))
            elif not favorite and old is not None:
                connection.execute(delete(job_favorites).where(job_favorites.c.job_id == record_id))
        return self.get_job(record_id)

    def delete_job(self, record_id: int) -> None:
        try:
            with self.engine.begin() as connection:
                if connection.scalar(select(jobs.c.id).where(jobs.c.id == record_id)) is None:
                    raise AssetNotFoundError
                if (connection.scalar(select(match_reports.c.id).where(
                        match_reports.c.job_id == record_id).limit(1)) is not None
                        or connection.scalar(select(applications_table.c.id).where(
                            applications_table.c.job_id == record_id).limit(1)) is not None):
                    raise AssetInUseError
                connection.execute(delete(jobs).where(jobs.c.id == record_id))
        except IntegrityError as exc:
            raise AssetInUseError from exc

    def list_reports(self, resume_id: int | None, job_id: int | None) -> list[ReportSummary]:
        source = match_reports.join(resumes, match_reports.c.resume_id == resumes.c.id)
        source = source.join(jobs, match_reports.c.job_id == jobs.c.id)
        statement = self._report_statement(source)
        if resume_id is not None:
            statement = statement.where(match_reports.c.resume_id == resume_id)
        if job_id is not None:
            statement = statement.where(match_reports.c.job_id == job_id)
        with self.engine.connect() as connection:
            rows = connection.execute(statement.order_by(match_reports.c.id.desc()).limit(100))\
                .mappings().all()
        return [ReportSummary.model_validate({
            key: value for key, value in row.items() if key != "result"
        }) for row in rows]

    def get_report(self, record_id: int) -> ReportDetail:
        source = match_reports.join(resumes, match_reports.c.resume_id == resumes.c.id)
        source = source.join(jobs, match_reports.c.job_id == jobs.c.id)
        with self.engine.connect() as connection:
            row = connection.execute(self._report_statement(source)
                                     .where(match_reports.c.id == record_id))\
                .mappings().first()
        if row is None:
            raise AssetNotFoundError
        return ReportDetail.model_validate(row)

    def save_report(self, resume_id: int, job_id: int, result: MatchResult,
                    provider: str, model: str) -> ReportDetail:
        try:
            with self.engine.begin() as connection:
                if (connection.scalar(select(resumes.c.id).where(resumes.c.id == resume_id)) is None
                        or connection.scalar(select(jobs.c.id).where(jobs.c.id == job_id)) is None):
                    raise AssetNotFoundError
                record_id = connection.execute(insert(match_reports).values(
                    source_key=f"reanalyze:{uuid4().hex}", resume_id=resume_id, job_id=job_id,
                    overall_score=result.overall_score, recommendation=result.recommendation,
                    result=result.model_dump(mode="json"), provider=provider, model=model,
                    created_at=datetime.now(UTC),
                )).inserted_primary_key[0]
        except IntegrityError as exc:
            raise AssetNotFoundError from exc
        return self.get_report(int(record_id))

    @staticmethod
    def _resume(row) -> ResumeAsset:
        return ResumeAsset.model_validate({
            "id": row["id"], "filename": row["filename"],
            "profile": row["candidate_profile"], "created_at": row["created_at"],
        })

    @staticmethod
    def _job(row) -> JobAsset:
        return JobAsset.model_validate({
            "id": row["id"], "profile": row["job_profile"], "job_url": row["job_url"],
            "favorite": row["favorite_id"] is not None, "created_at": row["created_at"],
        })

    @staticmethod
    def _report_statement(source):
        return select(
            match_reports.c.id, match_reports.c.resume_id, match_reports.c.job_id,
            resumes.c.filename.label("resume_filename"), jobs.c.title.label("job_title"),
            jobs.c.company, match_reports.c.overall_score, match_reports.c.recommendation,
            match_reports.c.provider, match_reports.c.model, match_reports.c.created_at,
            match_reports.c.result,
        ).select_from(source)
