"""在本机终端创建额外账号；新账号从空资料库开始。"""

from getpass import getpass

from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.services.auth_repository import AuthRepository


def main() -> int:
    engine = None
    try:
        username = input("新账号用户名：").strip()
        password = getpass("新账号密码（12～128 字符，不会回显）：")
        if password != getpass("再次输入密码："):
            raise ValueError("两次输入的密码不一致。")
        engine = create_engine(get_settings().validated_database_url(), pool_pre_ping=True,
                               connect_args={"connect_timeout": 10})
        schema = inspect(engine)
        columns = {item["name"]: item for item in schema.get_columns("job_imports")}
        indexes = {item["name"] for item in schema.get_indexes("job_imports")}
        indexes.update(item["name"] for item in schema.get_unique_constraints("job_imports"))
        if ("user_id" not in columns or columns["user_id"]["nullable"]
                or "uq_job_import_source_owner" not in indexes
                or "uq_job_import_source" in indexes
                or not AuthRepository(engine).has_users()):
            raise ValueError("请先运行初始账号升级脚本。")
        AuthRepository(engine).create_user(username, password)
        print("新账号已创建，资料库为空；未输出密码。")
        return 0
    except Exception as exc:
        original = getattr(exc, "orig", None)
        args = getattr(original, "args", ())
        code = args[0] if args and isinstance(args[0], int) else "无"
        print(f"创建账号失败：{type(exc).__name__}，数据库错误码={code}。")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
