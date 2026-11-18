"""显式管理空库初始化、完整旧库接入和后续 Alembic 升级。"""

import argparse
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, UniqueConstraint, create_engine, func, inspect, select
from sqlalchemy.engine import Connection, Engine

from app.core.config import get_settings
from app.core.database_schema import metadata

BASELINE_REVISION = "0001_current_schema"
# 仅允许显式审查过的最新版本；新增迁移时同步更新这里与 baseline_metadata。
HEAD_REVISION = "0002_user_assets_owner_index"
NEW_INDEX = "ix_user_assets_owner_type_id"


def baseline_metadata() -> MetaData:
    """冻结 0001 所对应的表模型，不包含 0002 新增的索引。"""
    snapshot = MetaData()
    for table in metadata.sorted_tables:
        table.to_metadata(snapshot)
    for index in list(snapshot.tables["user_assets"].indexes):
        if index.name == NEW_INDEX:
            snapshot.tables["user_assets"].indexes.remove(index)
    return snapshot


def validate_schema(connection: Connection, expected: MetaData, versioned: bool) -> None:
    inspector = inspect(connection)
    actual_tables = set(inspector.get_table_names())
    expected_tables = set(expected.tables)
    if versioned:
        expected_tables.add("alembic_version")
    if actual_tables != expected_tables:
        raise ValueError("表集合与目标版本不一致；请检查旧升级步骤。")

    for table in expected.tables.values():
        actual_pk = tuple(inspector.get_pk_constraint(table.name)["constrained_columns"])
        expected_pk = tuple(column.name for column in table.primary_key.columns)
        if actual_pk != expected_pk:
            raise ValueError("主键结构与目标版本不一致。")
        actual_unique = {
            tuple(item["column_names"])
            for item in inspector.get_unique_constraints(table.name)
        }
        expected_unique = {
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        if not expected_unique.issubset(actual_unique):
            raise ValueError("唯一约束与目标版本不一致。")

    differences = compare_metadata(
        MigrationContext.configure(connection, opts={"compare_type": True}), expected,
    )
    if differences:
        raise ValueError(f"库结构与目标版本存在 {len(differences)} 项差异；未修改版本号。")


def _config(connection: Connection) -> Config:
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


def _counts(connection: Connection) -> dict[str, int]:
    return {table.name: connection.scalar(select(func.count()).select_from(table))
            for table in metadata.tables.values()}


def run(engine: Engine, action: str) -> str:
    if engine.dialect.name != "mysql":
        raise ValueError("迁移命令仅支持 MySQL。")
    with engine.connect() as connection:
        names = set(inspect(connection).get_table_names())
        revision = MigrationContext.configure(connection).get_current_revision()

        if action == "status":
            if not names:
                return "空库；可运行 initialize。"
            if revision is None:
                validate_schema(connection, baseline_metadata(), versioned=False)
                return "未登记版本；十四表基线结构检查通过，可备份停写后运行 adopt。"
            if revision == HEAD_REVISION:
                validate_schema(connection, metadata, versioned=True)
                return f"当前版本 {revision}；结构检查通过。"
            if revision == BASELINE_REVISION:
                validate_schema(connection, baseline_metadata(), versioned=True)
                return f"当前版本 {revision}；基线结构检查通过，可运行 upgrade。"
            raise ValueError("数据库版本不属于当前迁移链。")

        if action == "initialize":
            if names:
                raise ValueError("initialize 仅接受完全空库。")
            connection.rollback()
            with connection.begin():
                command.upgrade(_config(connection), "head")
            validate_schema(connection, metadata, versioned=True)
            return f"空库已升级至 {HEAD_REVISION}。"

        if action == "adopt":
            if revision is not None or "alembic_version" in names:
                raise ValueError("数据库已有迁移版本；不能重复接入基线。")
            validate_schema(connection, baseline_metadata(), versioned=False)
            before = _counts(connection)
            connection.rollback()
            with connection.begin():
                command.stamp(_config(connection), BASELINE_REVISION)
                command.upgrade(_config(connection), "head")
            validate_schema(connection, metadata, versioned=True)
            if _counts(connection) != before:
                raise ValueError("迁移后业务表行数发生变化，请从备份核对。")
            return f"旧库已登记基线并升级至 {HEAD_REVISION}；业务行数不变。"

        if action == "upgrade":
            if revision is None:
                raise ValueError("尚无迁移版本；请先检查空库或旧库接入路径。")
            if revision == BASELINE_REVISION:
                validate_schema(connection, baseline_metadata(), versioned=True)
            elif revision == HEAD_REVISION:
                validate_schema(connection, metadata, versioned=True)
            else:
                raise ValueError("数据库版本不属于当前迁移链。")
            connection.rollback()
            with connection.begin():
                command.upgrade(_config(connection), "head")
            validate_schema(connection, metadata, versioned=True)
            return f"数据库已升级至 {HEAD_REVISION}。"

        raise ValueError("未知迁移动作。")


def main() -> int:
    parser = argparse.ArgumentParser(description="MySQL 数据库版本管理")
    parser.add_argument("action", choices=("status", "initialize", "adopt", "upgrade"))
    action = parser.parse_args().action
    engine = None
    try:
        engine = create_engine(get_settings().validated_database_url(), pool_pre_ping=True,
                               connect_args={"connect_timeout": 10})
        print(run(engine, action))
        return 0
    except Exception as exc:
        original = getattr(exc, "orig", None)
        args = getattr(original, "args", ())
        code = args[0] if args and isinstance(args[0], int) else "无"
        detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(f"迁移失败：{detail}；数据库错误码={code}。")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
