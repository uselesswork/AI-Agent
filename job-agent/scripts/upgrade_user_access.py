"""交互式创建初始账号并认领历史数据；执行前须备份、停止应用写入。"""

from getpass import getpass

from sqlalchemy import create_engine, inspect, insert, select, update

from app.core.config import get_settings
from app.core.database_schema import (
    applications_table, auth_sessions, job_imports, jobs, match_reports,
    resumes, user_assets, users, metadata,
)
from app.services.auth_repository import AuthRepository

OWNED_TABLES = (
    ("resume", resumes), ("job", jobs), ("report", match_reports),
    ("application", applications_table),
)


def prepare_schema(engine) -> None:
    if engine.dialect.name != "mysql":
        raise ValueError("该脚本只用于 MySQL；测试库请直接创建完整结构。")
    existing = set(inspect(engine).get_table_names())
    required = {"resumes", "jobs", "match_reports", "applications", "job_imports"}
    if not required.issubset(existing):
        raise ValueError("请先完成前十二阶段数据库初始化。")
    metadata.create_all(engine, tables=[users, auth_sessions, user_assets])
    columns = {item["name"] for item in inspect(engine).get_columns("job_imports")}
    if "user_id" not in columns:
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE job_imports ADD COLUMN user_id INT NULL")


def claim_legacy_data(engine, user_id: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    with engine.begin() as connection:
        for kind, table in OWNED_TABLES:
            ids = list(connection.scalars(select(table.c.id)))
            counts[table.name] = len(ids)
            for entity_id in ids:
                existing = connection.scalar(select(user_assets.c.user_id).where(
                    user_assets.c.entity_type == kind,
                    user_assets.c.entity_id == entity_id,
                ))
                if existing is None:
                    connection.execute(insert(user_assets).values(
                        entity_type=kind, entity_id=entity_id, user_id=user_id,
                    ))
                elif existing != user_id:
                    raise ValueError("发现历史数据已归属其他账号，已停止认领。")
        connection.execute(update(job_imports).where(job_imports.c.user_id.is_(None))
                           .values(user_id=user_id))
    return counts


def finish_schema(engine) -> None:
    with engine.connect() as connection:
        null_count = connection.scalar(select(job_imports.c.id).where(
            job_imports.c.user_id.is_(None)).limit(1))
    if null_count is not None:
        raise ValueError("仍有未归属的岗位来源记录，不能完成升级。")
    inspector = inspect(engine)
    indexes = {item["name"] for item in inspector.get_indexes("job_imports")}
    indexes.update(item["name"] for item in inspector.get_unique_constraints("job_imports"))
    if "uq_job_import_source_owner" not in indexes:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE job_imports ADD UNIQUE KEY uq_job_import_source_owner "
                "(user_id, source, board_token, external_id)"
            )
    if "uq_job_import_source" in indexes:
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE job_imports DROP INDEX uq_job_import_source")
    column = next(item for item in inspect(engine).get_columns("job_imports")
                  if item["name"] == "user_id")
    if column["nullable"]:
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE job_imports MODIFY COLUMN user_id INT NOT NULL")


def bootstrap(engine, username: str, password: str) -> dict[str, int]:
    prepare_schema(engine)
    repository = AuthRepository(engine)
    with engine.connect() as connection:
        accounts = connection.execute(select(users.c.id, users.c.username)).all()
    if not accounts:
        user_id = repository.create_user(username, password)
    elif len(accounts) == 1 and accounts[0].username == username.strip().lower():
        account = repository.authenticate(username, password)
        if account is None:
            raise ValueError("已有初始账号，但输入的密码不正确。")
        user_id = account[0]
    else:
        raise ValueError("数据库已有其他账号；不能再次自动认领历史数据。")
    counts = claim_legacy_data(engine, user_id)
    finish_schema(engine)
    return counts


def main() -> int:
    engine = None
    try:
        username = input("初始账号用户名（3～32 位英文字母/数字/_/-）：").strip()
        password = getpass("初始账号密码（12～128 字符，不会回显）：")
        confirmation = getpass("再次输入密码：")
        if password != confirmation:
            raise ValueError("两次输入的密码不一致。")
        engine = create_engine(get_settings().validated_database_url(), pool_pre_ping=True,
                               connect_args={"connect_timeout": 10})
        counts = bootstrap(engine, username, password)
        print("初始账号已就绪；旧资料已归属该账号，未输出密码。")
        for table, count in counts.items():
            print(f"{table}: {count}")
        return 0
    except Exception as exc:
        original = getattr(exc, "orig", None)
        args = getattr(original, "args", ())
        code = args[0] if args and isinstance(args[0], int) else "无"
        print(f"账号升级失败：{type(exc).__name__}，数据库错误码={code}。")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
