"""本地账号登录、登出及个人数据导出/删除。账号创建只允许本机脚本。"""

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api import applications
from app.core.request_auth import COOKIE_NAME
from app.models.auth import AccountDeleteRequest, AccountInfo, LoginRequest
from app.services.auth_repository import AuthRepository, SESSION_HOURS
from app.services.personal_data import delete_personal_data, export_personal_data

router = APIRouter(prefix="/api/auth", tags=["账号与个人数据"])


def _repository() -> AuthRepository:
    return AuthRepository(applications.get_repository().engine)


@router.get("/status")
def auth_status() -> dict[str, bool]:
    return {"configured": _repository().has_users()}


@router.post("/login", response_model=AccountInfo)
def login(data: LoginRequest, request: Request, response: Response) -> AccountInfo:
    repository = _repository()
    if not repository.has_users():
        raise HTTPException(status_code=503, detail="尚未创建本地账号，请先运行账号初始化脚本。")
    account = repository.authenticate(data.username, data.password)
    if account is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误。")
    user_id, username = account
    token, csrf_token = repository.create_session(user_id)
    local_http = (request.url.scheme == "http" and
                  request.url.hostname in {"localhost", "127.0.0.1"})
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_HOURS * 3600, path="/",
        httponly=True, samesite="strict", secure=not local_http,
    )
    response.headers["Cache-Control"] = "no-store"
    return AccountInfo(id=user_id, username=username, csrf_token=csrf_token)


@router.get("/me", response_model=AccountInfo)
def me(request: Request) -> AccountInfo:
    principal = request.state.principal
    return AccountInfo(id=principal.user_id, username=principal.username,
                       csrf_token=principal.csrf_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    _repository().revoke_session(request.state.principal.token_hash)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@router.get("/export")
def export_account(request: Request) -> JSONResponse:
    data = export_personal_data(applications.get_repository().engine,
                                request.state.principal.user_id)
    return JSONResponse(jsonable_encoder(data), headers={
        "Cache-Control": "no-store",
        "Content-Disposition": 'attachment; filename="job-agent-personal-data.json"',
    })


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(data: AccountDeleteRequest, request: Request) -> Response:
    if not data.confirmed:
        raise HTTPException(status_code=422, detail="必须明确确认删除账号和全部个人数据。")
    principal = request.state.principal
    account = _repository().authenticate(principal.username, data.password)
    if account is None or account[0] != principal.user_id:
        raise HTTPException(status_code=403, detail="密码验证失败。")
    try:
        delete_personal_data(applications.get_repository().engine, principal.user_id)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="仍有未能清理的关联数据，账号未删除。") from exc
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response
