"""本地多账号登录与个人数据操作输入。"""

from pydantic import Field

from app.models.candidate import StrictModel


class LoginRequest(StrictModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=1, max_length=128)


class AccountDeleteRequest(StrictModel):
    password: str = Field(min_length=1, max_length=128)
    confirmed: bool


class AccountInfo(StrictModel):
    id: int
    username: str
    csrf_token: str
