"""只为已有 MySQL 求职数据库增加第十一阶段草稿标注表。"""

from sqlalchemy import create_engine, func, inspect, select

from app.core.config import get_settings
from app.core.database_schema import draft_annotations, metadata


def upgrade(engine) -> int:
    if engine.dialect.name != "mysql":
        raise ValueError("该脚本只用于 MySQL；测试库请直接创建完整结构。")
    existing = set(inspect(engine).get_table_names())
    if not {"draft_versions", "application_sources"}.issubset(existing):
        raise ValueError("请先完成草稿版本表与投递原文表初始化。")
    metadata.create_all(engine, tables=[draft_annotations])
    with engine.connect() as connection:
        return int(connection.scalar(select(func.count()).select_from(draft_annotations)) or 0)


def main() -> int:
    engine = None
    try:
        engine = create_engine(get_settings().validated_database_url(), pool_pre_ping=True,
                               connect_args={"connect_timeout": 10})
        count = upgrade(engine)
        print(f"草稿标注表已就绪，现有标注 {count} 条；未写入示例标注或修改原文。")
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
