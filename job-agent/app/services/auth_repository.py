"""账号、慢哈希密码和服务端会话。原始会话令牌不写入数据库。"""

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import insert, select, delete, func, inspect
from sqlalchemy.engine import Engine

from app.core.database_schema import auth_sessions, users

SESSION_HOURS = 12
SCRYPT_N = 2**17
SCRYPT_MAXMEM = 256 * 1024 * 1024


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    csrf_token: str
    token_hash: str


class AuthRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def hash_password(password: str) -> str:
        if len(password) < 12 or len(password) > 128:
            raise ValueError("密码长度须为 12～128 个字符。")
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N,
                                r=8, p=1, maxmem=SCRYPT_MAXMEM, dklen=32)
        return "scrypt$131072$8$1$" + base64.b64encode(salt).decode() + "$" + \
            base64.b64encode(digest).decode()

    @staticmethod
    def verify_password(password: str, stored: str) -> bool:
        try:
            algorithm, n, r, p, salt_text, hash_text = stored.split("$")
            if algorithm != "scrypt" or (n, r, p) != ("131072", "8", "1"):
                return False
            salt = base64.b64decode(salt_text, validate=True)
            expected = base64.b64decode(hash_text, validate=True)
            digest = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                                    n=int(n), r=int(r), p=int(p),
                                    maxmem=SCRYPT_MAXMEM, dklen=len(expected))
            return hmac.compare_digest(digest, expected)
        except (ValueError, TypeError):
            return False

    def has_users(self) -> bool:
        if not inspect(self.engine).has_table("users"):
            return False
        with self.engine.connect() as connection:
            return bool(connection.scalar(select(func.count()).select_from(users)))

    def create_user(self, username: str, password: str) -> int:
        normalized = username.strip().lower()
        if not 3 <= len(normalized) <= 32 or not all(
                character.isascii() and (character.isalnum() or character in "_-")
                for character in normalized):
            raise ValueError("用户名须为 3～32 位英文字母、数字、下划线或连字符。")
        password_hash = self.hash_password(password)
        with self.engine.begin() as connection:
            result = connection.execute(insert(users).values(
                username=normalized, password_hash=password_hash,
                created_at=datetime.now(UTC),
            ))
            return int(result.inserted_primary_key[0])

    def authenticate(self, username: str, password: str) -> tuple[int, str] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(users.c.id, users.c.username, users.c.password_hash)
                                     .where(users.c.username == username.strip().lower())).first()
        if row is None or not self.verify_password(password, row.password_hash):
            return None
        return row.id, row.username

    def create_session(self, user_id: int) -> tuple[str, str]:
        raw_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            connection.execute(insert(auth_sessions).values(
                token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                user_id=user_id, csrf_token=csrf_token, created_at=now,
                expires_at=now + timedelta(hours=SESSION_HOURS),
            ))
        return raw_token, csrf_token

    def session(self, raw_token: str) -> Principal | None:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        with self.engine.connect() as connection:
            row = connection.execute(select(
                auth_sessions.c.user_id, auth_sessions.c.csrf_token,
                auth_sessions.c.expires_at, users.c.username,
            ).select_from(auth_sessions.join(users, auth_sessions.c.user_id == users.c.id))
                .where(auth_sessions.c.token_hash == token_hash)).first()
        if row is None:
            return None
        expiry = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
        if expiry <= datetime.now(UTC):
            return None
        return Principal(row.user_id, row.username, row.csrf_token, token_hash)

    def revoke_session(self, token_hash: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(delete(auth_sessions).where(auth_sessions.c.token_hash == token_hash))
