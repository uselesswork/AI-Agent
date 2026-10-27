"""只为已有 MySQL 求职数据库增加第十二阶段投递日程表。"""

from sqlalchemy import create_engine, func, inspect, select

from app.core.config import get_settings
from app.core.database_schema import application_milestones, metadata


def upgrade(engine) -> int:
    if engine.dialect.name != "mysql":
        raise ValueError("该脚本只用于 MySQL；测试库请直接创建完整结构。")
    if "applications" not in inspect(engine).get_table_names():
        raise ValueError("请先完成 applications 表初始化。")
    metadata.create_all(engine, tables=[application_milestones])
    with engine.connect() as connection:
        return int(connection.scalar(select(func.count()).select_from(application_milestones)) or 0)


def main() -> int:
    engine = None
    try:
        engine = create_engine(get_settings().validated_database_url(), pool_pre_ping=True,
                               connect_args={"connect_timeout": 10})
        count = upgrade(engine)
        print(f"投递日程表已就绪，现有日程 {count} 条；未写入示例日期或自动发送提醒。")
        return 0
    except Exception as exc:
        original = getattr(exc, "orig", None)
        args = getattr(original, "args", ())
        code = args[0] if args and isinstance(args[0], int) else "无"
        print(f"升级失败：{type(exc).__name__}，数据库错误码={code}。")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
