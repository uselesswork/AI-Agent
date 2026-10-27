"""十一表结构；applications 的旧快照字段保留以兼容现有接口。"""

from sqlalchemy import (
    JSON, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import LONGTEXT

metadata = MetaData()

resumes = Table(
    "resumes", metadata,
    Column("id", Integer, primary_key=True),
    Column("content_key", String(64), nullable=False, unique=True),
    Column("filename", String(255), nullable=False),
    Column("raw_text", Text),
    Column("candidate_profile", JSON, nullable=False),
    Column("created_at", DateTime, nullable=False),
    mysql_charset="utf8mb4",
)

jobs = Table(
    "jobs", metadata,
    Column("id", Integer, primary_key=True),
    Column("source_key", String(100), nullable=False, unique=True),
    Column("title", String(255)),
    Column("company", String(255)),
    Column("location", String(255)),
    Column("raw_description", Text),
    Column("job_profile", JSON, nullable=False),
    Column("job_url", String(2000)),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    mysql_charset="utf8mb4",
)

job_favorites = Table(
    "job_favorites", metadata,
    Column("job_id", Integer, ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    mysql_charset="utf8mb4",
)

job_imports = Table(
    "job_imports", metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False,
           index=True),
    Column("source", String(20), nullable=False),
    Column("board_token", String(100), nullable=False),
    Column("external_id", String(100), nullable=False),
    Column("source_url", String(2000), nullable=False),
    Column("imported_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("source", "board_token", "external_id", name="uq_job_import_source"),
    mysql_charset="utf8mb4",
)

match_reports = Table(
    "match_reports", metadata,
    Column("id", Integer, primary_key=True),
    Column("source_key", String(100), nullable=False, unique=True),
    Column("resume_id", Integer, ForeignKey("resumes.id", ondelete="RESTRICT"),
           nullable=False, index=True),
    Column("job_id", Integer, ForeignKey("jobs.id", ondelete="RESTRICT"),
           nullable=False, index=True),
    Column("overall_score", Integer, nullable=False, index=True),
    Column("recommendation", String(30), nullable=False),
    Column("result", JSON, nullable=False),
    Column("provider", String(20), nullable=False),
    Column("model", String(255), nullable=False),
    Column("created_at", DateTime, nullable=False),
    mysql_charset="utf8mb4",
)

applications_table = Table(
    "applications", metadata,
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
    Column("resume_id", Integer, ForeignKey("resumes.id", name="fk_app_resume",
                                           ondelete="RESTRICT"), index=True),
    Column("job_id", Integer, ForeignKey("jobs.id", name="fk_app_job",
                                        ondelete="RESTRICT"), index=True),
    Column("match_report_id", Integer, ForeignKey("match_reports.id", name="fk_app_report",
                                                 ondelete="RESTRICT"), index=True),
    Column("applied_at", DateTime),
    mysql_charset="utf8mb4",
)

application_events = Table(
    "application_events", metadata,
    Column("id", Integer, primary_key=True),
    Column("application_id", Integer,
           ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("event_type", String(30), nullable=False),
    Column("from_status", String(20)),
    Column("to_status", String(20), nullable=False),
    Column("note", Text),
    Column("occurred_at", DateTime, nullable=False),
    mysql_charset="utf8mb4",
)

draft_versions = Table(
    "draft_versions", metadata,
    Column("id", Integer, primary_key=True),
    Column("application_id", Integer,
           ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("version", Integer, nullable=False),
    Column("resume", JSON, nullable=False),
    Column("cover_letter", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("reviewed_at", DateTime(timezone=True)),
    UniqueConstraint("application_id", "version", name="uq_draft_application_version"),
    mysql_charset="utf8mb4",
)

application_sources = Table(
    "application_sources", metadata,
    Column("application_id", Integer,
           ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True),
    Column("resume_text", Text().with_variant(LONGTEXT, "mysql"), nullable=False),
    Column("job_description", Text().with_variant(LONGTEXT, "mysql"), nullable=False),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    mysql_charset="utf8mb4",
)

draft_annotations = Table(
    "draft_annotations", metadata,
    Column("id", Integer, primary_key=True),
    Column("version_id", Integer,
           ForeignKey("draft_versions.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("application_id", Integer,
           ForeignKey("application_sources.application_id", ondelete="CASCADE"),
           nullable=False, index=True),
    Column("document", String(10), nullable=False),
    Column("section_index", Integer, nullable=False),
    Column("line_index", Integer, nullable=False),
    Column("source_kind", String(10), nullable=False),
    Column("source_quote", Text, nullable=False),
    Column("note", String(500)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("version_id", "document", "section_index", "line_index",
                     name="uq_annotation_version_line"),
    mysql_charset="utf8mb4",
)

application_milestones = Table(
    "application_milestones", metadata,
    Column("id", Integer, primary_key=True),
    Column("application_id", Integer,
           ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("kind", String(20), nullable=False),
    Column("title", String(200), nullable=False),
    Column("scheduled_at", DateTime(timezone=True), nullable=False, index=True),
    Column("notes", Text),
    Column("completed_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    mysql_charset="utf8mb4",
)
