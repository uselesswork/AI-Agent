"""本机交互式重置已有账号密码；不读取旧密码，不写入 .env。"""

from getpass import getpass

from sqlalchemy import create_engine, select

from app.core.config import get_settings
from app.core.database_schema import users
from app.services.auth_repository import AuthRepository


def main() -> int:
    engine = None
    try:
        username = input("要重置密码的账号用户名：").strip().lower()
        engine = create_engine(get_settings().validated_database_url(), pool_pre_ping=True,
                               connect_args={"connect_timeout": 10})
        with engine.connect() as connection:
            exists = connection.scalar(select(users.c.id).where(users.c.username == username))
        if exists is None:
            raise ValueError("账号不存在，密码未修改。")
        confirmed = input(f"将重置 {username} 的密码并退出该账号所有设备；再次输入用户名确认：")
        if confirmed.strip().lower() != username:
            raise ValueError("确认用户名不一致，密码未修改。")
        new_password = getpass("新密码（12～128 字符，不会回显）：")
        if new_password != getpass("再次输入新密码："):
            raise ValueError("两次输入的密码不一致，密码未修改。")
        AuthRepository(engine).reset_password(username, new_password)
        print("密码已重置，原有登录会话已全部失效；请使用新密码重新登录。")
        return 0
    except ValueError as exc:
        print(f"重置失败：{exc}")
        return 1
    except Exception as exc:
        # 数据库异常可能包含连接地址，禁止直接输出异常文本。
        original = getattr(exc, "orig", None)
        args = getattr(original, "args", ())
        code = args[0] if args and isinstance(args[0], int) else "无"
        print(f"重置失败：{type(exc).__name__}，数据库错误码={code}。")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
