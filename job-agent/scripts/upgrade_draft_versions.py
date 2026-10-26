"""只为已有 MySQL 求职数据库新增草稿版本表，不导入测试数据。"""

from sqlalchemy import create_engine, func, inspect, select

from app.core.config import get_settings
from app.core.database_schema import draft_versions, metadata


def upgrade(engine) -> int:
    if engine.dialect.name != "mysql":
        raise ValueError("该脚本只用于 MySQL；测试库请直接创建完整结构。")
    if "applications" not in inspect(engine).get_table_names():
        raise ValueError("请先完成第四阶段的 applications 表初始化。")
    metadata.create_all(engine, tables=[draft_versions])
    with engine.connect() as connection:
        return int(connection.scalar(select(func.count()).select_from(draft_versions)) or 0)


def main() -> int:
    engine = None
    try:
        engine = create_engine(get_settings().validated_database_url(), pool_pre_ping=True,
                               connect_args={"connect_timeout": 10})
        count = upgrade(engine)
        print(f"草稿版本表已就绪，现有版本记录 {count} 条；没有修改原有五张表或导入测试数据。")
        return 0
    except Exception as exc:
        # 不输出可能携带账号或密码的异常字符串。
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
