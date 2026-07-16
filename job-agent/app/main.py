from fastapi import FastAPI

from app.api.resumes import router as resumes_router

app = FastAPI(title="Job Agent", version="0.1.0")
app.include_router(resumes_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
