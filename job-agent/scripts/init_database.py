"""MySQL 增量初始化、旧记录关联回填、测试数据导入和回读。"""

from datetime import UTC, datetime

from sqlalchemy import create_engine, func, inspect, select, text, update
from sqlalchemy.schema import AddConstraint, CreateColumn

from app.core.config import get_settings
from app.core.database_schema import (
    application_events, application_sources, applications_table, draft_versions,
    jobs, match_reports, metadata, resumes,
)
from app.services.application_relations import add_event, attach_snapshot
from scripts.seed_applications import seed, verify


def upgrade_schema(engine):
    """只添加缺失表、列、索引和外键；不删除、重建或覆盖旧列。"""
    if engine.dialect.name != "mysql":
        raise ValueError("旧表升级仅用于 MySQL；测试库直接创建完整结构。")
    metadata.create_all(engine)
    existing = {column["name"] for column in inspect(engine).get_columns("applications")}
    for name in ("resume_id", "job_id", "match_report_id", "applied_at"):
        if name not in existing:
            column = applications_table.c[name]
            definition = str(CreateColumn(column).compile(dialect=engine.dialect))
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE applications ADD COLUMN {definition}"))
    known_fk = {item["name"] for item in inspect(engine).get_foreign_keys("applications")}
    for constraint in applications_table.foreign_key_constraints:
        if constraint.name not in known_fk:
            with engine.begin() as connection:
                connection.execute(AddConstraint(constraint))
    indexes = {item["name"] for item in inspect(engine).get_indexes("applications")}
    for index in applications_table.indexes:
        if index.name not in indexes:
            index.create(engine)


def backfill(engine):
    migrated = 0
    with engine.begin() as connection:
        rows = connection.execute(select(applications_table).with_for_update()).mappings().all()
        for row in rows:
            if all(row[key] is not None for key in ("resume_id", "job_id", "match_report_id")):
                continue
            links = attach_snapshot(connection, dict(row), f"legacy-application:{row['id']}")
            connection.execute(update(applications_table).where(
                applications_table.c.id == row["id"]).values(**links))
            add_event(connection, row["id"], "snapshot", None, row["status"],
                      datetime.now(UTC), "旧记录迁移时的状态快照；不是历史状态变化时间")
            migrated += 1
    return migrated


def verify_relations(engine):
    with engine.connect() as connection:
        counts = {table.name: connection.scalar(select(func.count()).select_from(table))
                  for table in (resumes, jobs, match_reports, applications_table,
                                application_events, draft_versions, application_sources)}
        joined = applications_table.join(resumes).join(
            jobs, applications_table.c.job_id == jobs.c.id).join(
            match_reports, applications_table.c.match_report_id == match_reports.c.id)
        linked = connection.scalar(select(func.count()).select_from(joined))
        if linked != counts["applications"]:
            raise ValueError("存在未完成关联的投递记录")
        inconsistent = connection.scalar(select(func.count()).select_from(joined).where(
            (applications_table.c.resume_id != match_reports.c.resume_id)
            | (applications_table.c.job_id != match_reports.c.job_id)))
        if inconsistent:
            raise ValueError("投递记录与报告关联不一致")
    return counts


def main():
    engine = None
    try:
        engine = create_engine(get_settings().validated_database_url(), pool_pre_ping=True,
                               connect_args={"connect_timeout": 10})
        # 同一个初始化工具不允许并行执行。应用写入仍需在维护时段暂停。
        with engine.connect() as lock:
            acquired = lock.scalar(text("SELECT GET_LOCK('job_agent_schema_v2', 10)"))
            if acquired != 1:
                raise RuntimeError("无法获得初始化锁")
            try:
                upgrade_schema(engine)
                migrated = backfill(engine)
                inserted, skipped = seed(engine)
                counts = verify_relations(engine)
                samples = verify(engine)
                print(f"旧记录关联回填 {migrated} 条；新增测试记录 {inserted} 条；跳过 {skipped} 条。")
                for name, count in counts.items():
                    print(f"{name}: {count}")
                print(f"关联完整性检查通过，测试报告回读通过：{len(samples)} 条。")
            finally:
                lock.execute(text("SELECT RELEASE_LOCK('job_agent_schema_v2')"))
        return 0
    except Exception as exc:
        original = getattr(exc, "orig", None)
        args = getattr(original, "args", ())
        code = args[0] if args and isinstance(args[0], int) else "无"
        print(f"初始化失败：{type(exc).__name__}，数据库错误码={code}。")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
