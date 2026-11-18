"""MySQL 迁移：空库、旧库接入、拒绝结构漂移。"""

import pytest
from alembic import command
from sqlalchemy import func, inspect, select, text

from app.core.database_schema import users
from app.services.auth_repository import AuthRepository
from scripts.manage_migrations import (
    BASELINE_REVISION, HEAD_REVISION, _config, baseline_metadata, run,
)

pytestmark = pytest.mark.mysql_integration


def test_empty_database_upgrades_to_head(mysql_test_engine) -> None:
    assert run(mysql_test_engine, "status") == "空库；可运行 initialize。"
    assert HEAD_REVISION in run(mysql_test_engine, "initialize")
    assert HEAD_REVISION in run(mysql_test_engine, "status")
    assert HEAD_REVISION in run(mysql_test_engine, "upgrade")
    with mysql_test_engine.connect() as connection:
        assert len(inspect(connection).get_table_names()) == 15
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == HEAD_REVISION
        assert connection.scalar(select(func.count()).select_from(users)) == 0
        indexes = {item["name"] for item in inspect(connection).get_indexes("user_assets")}
        assert "ix_user_assets_owner_type_id" in indexes
    AuthRepository(mysql_test_engine).create_user("fresh_migration_owner", "TestMigrationPass-A1")
    with mysql_test_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(users)) == 1
    with pytest.raises(ValueError, match="仅接受完全空库"):
        run(mysql_test_engine, "initialize")


def test_existing_full_schema_adopts_without_changing_rows(mysql_test_engine) -> None:
    baseline_metadata().create_all(mysql_test_engine)
    AuthRepository(mysql_test_engine).create_user("migration_owner", "TestMigrationPass-A1")
    assert "基线结构检查通过" in run(mysql_test_engine, "status")
    assert HEAD_REVISION in run(mysql_test_engine, "adopt")
    with mysql_test_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(users)) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == HEAD_REVISION
    with pytest.raises(ValueError, match="不能重复接入"):
        run(mysql_test_engine, "adopt")


def test_existing_schema_drift_blocks_adoption(mysql_test_engine) -> None:
    baseline_metadata().create_all(mysql_test_engine)
    with mysql_test_engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE jobs DROP COLUMN location")
    with pytest.raises(ValueError, match="库结构与目标版本存在"):
        run(mysql_test_engine, "adopt")
    with mysql_test_engine.connect() as connection:
        assert "alembic_version" not in inspect(connection).get_table_names()


def test_stamped_baseline_upgrades_to_head(mysql_test_engine) -> None:
    baseline_metadata().create_all(mysql_test_engine)
    with mysql_test_engine.begin() as connection:
        command.stamp(_config(connection), BASELINE_REVISION)
    assert BASELINE_REVISION in run(mysql_test_engine, "status")
    assert HEAD_REVISION in run(mysql_test_engine, "upgrade")
    assert HEAD_REVISION in run(mysql_test_engine, "status")


def test_stamped_drift_blocks_upgrade(mysql_test_engine) -> None:
    baseline_metadata().create_all(mysql_test_engine)
    with mysql_test_engine.begin() as connection:
        command.stamp(_config(connection), BASELINE_REVISION)
        connection.exec_driver_sql("ALTER TABLE jobs DROP COLUMN location")
    with pytest.raises(ValueError, match="库结构与目标版本存在"):
        run(mysql_test_engine, "upgrade")
    with mysql_test_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == BASELINE_REVISION
        indexes = {item["name"] for item in inspect(connection).get_indexes("user_assets")}
        assert "ix_user_assets_owner_type_id" not in indexes
