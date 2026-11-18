"""十四表结构基线

Revision ID: 0001_current_schema
Revises: None
Create Date: 2026-11-18 15:52:39.103367
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '0001_current_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 已在隔离 MySQL 与原十四表结构对照；作为固定基线保留。
    op.create_table('jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_key', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('company', sa.String(length=255), nullable=True),
    sa.Column('location', sa.String(length=255), nullable=True),
    sa.Column('raw_description', sa.Text(), nullable=True),
    sa.Column('job_profile', sa.JSON(), nullable=False),
    sa.Column('job_url', sa.String(length=2000), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_key'),
    mysql_charset='utf8mb4'
    )
    op.create_table('resumes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('content_key', sa.String(length=64), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=True),
    sa.Column('candidate_profile', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('content_key'),
    mysql_charset='utf8mb4'
    )
    op.create_table('user_assets',
    sa.Column('entity_type', sa.String(length=20), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('entity_type', 'entity_id'),
    mysql_charset='utf8mb4'
    )
    op.create_index(op.f('ix_user_assets_user_id'), 'user_assets', ['user_id'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=32), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username'),
    mysql_charset='utf8mb4'
    )
    op.create_table('auth_sessions',
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('csrf_token', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('token_hash'),
    mysql_charset='utf8mb4'
    )
    op.create_index(op.f('ix_auth_sessions_expires_at'), 'auth_sessions', ['expires_at'], unique=False)
    op.create_index(op.f('ix_auth_sessions_user_id'), 'auth_sessions', ['user_id'], unique=False)
    op.create_table('job_favorites',
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('job_id'),
    mysql_charset='utf8mb4'
    )
    op.create_table('job_imports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('board_token', sa.String(length=100), nullable=False),
    sa.Column('external_id', sa.String(length=100), nullable=False),
    sa.Column('source_url', sa.String(length=2000), nullable=False),
    sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'source', 'board_token', 'external_id', name='uq_job_import_source_owner'),
    mysql_charset='utf8mb4'
    )
    op.create_index(op.f('ix_job_imports_job_id'), 'job_imports', ['job_id'], unique=False)
    op.create_index(op.f('ix_job_imports_user_id'), 'job_imports', ['user_id'], unique=False)
    op.create_table('match_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_key', sa.String(length=100), nullable=False),
    sa.Column('resume_id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('overall_score', sa.Integer(), nullable=False),
    sa.Column('recommendation', sa.String(length=30), nullable=False),
    sa.Column('result', sa.JSON(), nullable=False),
    sa.Column('provider', sa.String(length=20), nullable=False),
    sa.Column('model', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_key'),
    mysql_charset='utf8mb4'
    )
    op.create_index(op.f('ix_match_reports_job_id'), 'match_reports', ['job_id'], unique=False)
    op.create_index(op.f('ix_match_reports_overall_score'), 'match_reports', ['overall_score'], unique=False)
    op.create_index(op.f('ix_match_reports_resume_id'), 'match_reports', ['resume_id'], unique=False)
    op.create_table('applications',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('resume_filename', sa.String(length=255), nullable=False),
    sa.Column('candidate_profile', sa.JSON(), nullable=False),
    sa.Column('job_profile', sa.JSON(), nullable=False),
    sa.Column('match_result', sa.JSON(), nullable=False),
    sa.Column('provider', sa.String(length=20), nullable=False),
    sa.Column('model', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('job_url', sa.String(length=2000), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('resume_id', sa.Integer(), nullable=True),
    sa.Column('job_id', sa.Integer(), nullable=True),
    sa.Column('match_report_id', sa.Integer(), nullable=True),
    sa.Column('applied_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], name='fk_app_job', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['match_report_id'], ['match_reports.id'], name='fk_app_report', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], name='fk_app_resume', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4'
    )
    op.create_index(op.f('ix_applications_job_id'), 'applications', ['job_id'], unique=False)
    op.create_index(op.f('ix_applications_match_report_id'), 'applications', ['match_report_id'], unique=False)
    op.create_index(op.f('ix_applications_resume_id'), 'applications', ['resume_id'], unique=False)
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'], unique=False)
    op.create_index(op.f('ix_applications_updated_at'), 'applications', ['updated_at'], unique=False)
    op.create_table('application_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('application_id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(length=30), nullable=False),
    sa.Column('from_status', sa.String(length=20), nullable=True),
    sa.Column('to_status', sa.String(length=20), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('occurred_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4'
    )
    op.create_index(op.f('ix_application_events_application_id'), 'application_events', ['application_id'], unique=False)
    op.create_table('application_milestones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('application_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4'
    )
    op.create_index(op.f('ix_application_milestones_application_id'), 'application_milestones', ['application_id'], unique=False)
    op.create_index(op.f('ix_application_milestones_scheduled_at'), 'application_milestones', ['scheduled_at'], unique=False)
    op.create_table('application_sources',
    sa.Column('application_id', sa.Integer(), nullable=False),
    sa.Column('resume_text', sa.Text().with_variant(mysql.LONGTEXT(), 'mysql'), nullable=False),
    sa.Column('job_description', sa.Text().with_variant(mysql.LONGTEXT(), 'mysql'), nullable=False),
    sa.Column('stored_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('application_id'),
    mysql_charset='utf8mb4'
    )
    op.create_table('draft_versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('application_id', sa.Integer(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('resume', sa.JSON(), nullable=False),
    sa.Column('cover_letter', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'version', name='uq_draft_application_version'),
    mysql_charset='utf8mb4'
    )
    op.create_index(op.f('ix_draft_versions_application_id'), 'draft_versions', ['application_id'], unique=False)
    op.create_table('draft_annotations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('version_id', sa.Integer(), nullable=False),
    sa.Column('application_id', sa.Integer(), nullable=False),
    sa.Column('document', sa.String(length=10), nullable=False),
    sa.Column('section_index', sa.Integer(), nullable=False),
    sa.Column('line_index', sa.Integer(), nullable=False),
    sa.Column('source_kind', sa.String(length=10), nullable=False),
    sa.Column('source_quote', sa.Text(), nullable=False),
    sa.Column('note', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['application_sources.application_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['version_id'], ['draft_versions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('version_id', 'document', 'section_index', 'line_index', name='uq_annotation_version_line'),
    mysql_charset='utf8mb4'
    )
    op.create_index(op.f('ix_draft_annotations_application_id'), 'draft_annotations', ['application_id'], unique=False)
    op.create_index(op.f('ix_draft_annotations_version_id'), 'draft_annotations', ['version_id'], unique=False)



def downgrade() -> None:
    raise RuntimeError("十四表基线不支持降级删除；请从已验证的备份恢复。")
