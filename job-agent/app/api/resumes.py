from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.config import LLMConfigurationError
from app.models.candidate import ResumeAnalysisResponse
from app.services.document_parser import (
    DocumentParseError,
    EmptyDocumentTextError,
    extract_document_text,
)
from app.services.llm import LLMServiceError
from app.services.resume_analyzer import build_resume_analyzer

router = APIRouter(prefix="/api/resumes", tags=["简历"])

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class ResumeParseResponse(BaseModel):
    filename: str
    file_type: str
    character_count: int
    text: str


@dataclass(frozen=True)
class ParsedResume:
    filename: str
    file_type: str
    text: str


async def read_uploaded_resume(file: UploadFile) -> ParsedResume:
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="仅支持 PDF、DOCX 和 TXT 格式的简历。",
        )

    content = await file.read(MAX_FILE_SIZE + 1)
    await file.close()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传文件为空。",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="文件大小不能超过 10 MB。",
        )

    try:
        text = extract_document_text(content, extension)
    except EmptyDocumentTextError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DocumentParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ParsedResume(
        filename=filename,
        file_type=extension.removeprefix("."),
        text=text,
    )


@router.post("/parse", response_model=ResumeParseResponse)
async def parse_resume(file: UploadFile = File(...)) -> ResumeParseResponse:
    parsed = await read_uploaded_resume(file)
    return ResumeParseResponse(
        filename=parsed.filename,
        file_type=parsed.file_type,
        character_count=len(parsed.text),
        text=parsed.text,
    )


@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(file: UploadFile = File(...)) -> ResumeAnalysisResponse:
    parsed = await read_uploaded_resume(file)
    try:
        analyzer = build_resume_analyzer()
        profile = await analyzer.analyze(parsed.text)
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ResumeAnalysisResponse(
        filename=parsed.filename,
        provider=analyzer.provider,
        model=analyzer.model,
        profile=profile,
    )
