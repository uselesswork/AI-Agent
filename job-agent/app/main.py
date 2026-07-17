from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.jobs import router as jobs_router
from app.api.matches import router as matches_router
from app.api.resumes import router as resumes_router

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Job Agent", version="0.1.0")
app.include_router(resumes_router)
app.include_router(jobs_router)
app.include_router(matches_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/upload", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
