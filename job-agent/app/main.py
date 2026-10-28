from pathlib import Path

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse

from app.api import applications
from app.core import request_auth
from app.core.user_scope import bind_user, reset_user
from fastapi.staticfiles import StaticFiles

from app.api.applications import router as applications_router
from app.api.auth import router as auth_router
from app.api.discovery import router as discovery_router
from app.api.jobs import router as jobs_router
from app.api.library import router as library_router
from app.api.matches import router as matches_router
from app.api.planning import router as planning_router
from app.api.resumes import router as resumes_router

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Job Agent", version="0.1.0")


@app.middleware("http")
async def require_api_login(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)
    if path in {"/api/auth/login", "/api/auth/status"}:
        try:
            request_auth.check_origin(request)
        except request_auth.AuthFailure as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        return await call_next(request)
    try:
        principal = request_auth.resolve_request(request, applications.get_repository().engine)
    except request_auth.AuthFailure as exc:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code,
                            headers={"Cache-Control": "no-store"})
    request.state.principal = principal
    token = bind_user(principal.user_id)
    try:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response
    finally:
        reset_user(token)
app.include_router(resumes_router)
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(matches_router)
app.include_router(applications_router)
app.include_router(library_router)
app.include_router(discovery_router)
app.include_router(planning_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/upload", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
