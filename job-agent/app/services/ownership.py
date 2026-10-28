"""顶层资料归属表；所有按 ID 读取/写入路径均需校验归属。"""

import hashlib

from sqlalchemy import delete, insert, select

from app.core.database_schema import user_assets
from app.core.user_scope import current_user_id


def owner_key(value: str) -> str:
    user_id = current_user_id()
    return hashlib.sha256(f"user:{user_id}:{value}".encode("utf-8")).hexdigest()


def owned_ids(entity_type: str):
    return select(user_assets.c.entity_id).where(
        user_assets.c.user_id == current_user_id(),
        user_assets.c.entity_type == entity_type,
    )


def is_owned(connection, entity_type: str, entity_id: int) -> bool:
    return connection.scalar(select(user_assets.c.entity_id).where(
        user_assets.c.user_id == current_user_id(),
        user_assets.c.entity_type == entity_type,
        user_assets.c.entity_id == entity_id,
    )) is not None


def register_owner(connection, entity_type: str, entity_id: int) -> None:
    connection.execute(insert(user_assets).values(
        entity_type=entity_type, entity_id=int(entity_id), user_id=current_user_id(),
    ))


def remove_owner(connection, entity_type: str, entity_id: int) -> None:
    connection.execute(delete(user_assets).where(
        user_assets.c.entity_type == entity_type,
        user_assets.c.entity_id == entity_id,
        user_assets.c.user_id == current_user_id(),
    ))
