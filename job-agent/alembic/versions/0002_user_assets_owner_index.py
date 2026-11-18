"""为账号资料归属查询增加复合索引。

Revision ID: 0002_user_assets_owner_index
Revises: 0001_current_schema
"""

from alembic import op

revision = "0002_user_assets_owner_index"
down_revision = "0001_current_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_user_assets_owner_type_id", "user_assets",
        ["user_id", "entity_type", "entity_id"], unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_assets_owner_type_id", table_name="user_assets")
