from io import BytesIO

import pymupdf
from docx import Document
from fastapi.testclient import TestClient

from app.api import resumes
from app.main import app

client = TestClient(app)


def test_parse_txt_resume() -> None:
    response = client.post(
        "/api/resumes/parse",
        files={"file": ("resume.txt", "Python 开发实习".encode(), "text/plain")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "resume.txt",
        "file_type": "txt",
        "character_count": 11,
        "text": "Python 开发实习",
    }


def test_parse_pdf_resume() -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Backend internship")
    content = document.tobytes()
    document.close()

    response = client.post(
        "/api/resumes/parse",
        files={"file": ("resume.pdf", content, "application/pdf")},
    )

    assert response.status_code == 200
    assert "Backend internship" in response.json()["text"]


def test_parse_docx_resume() -> None:
    document = Document()
    document.add_paragraph("Java 后端开发")
    buffer = BytesIO()
    document.save(buffer)

    response = client.post(
        "/api/resumes/parse",
        files={
            "file": (
                "resume.docx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "Java 后端开发"


def test_reject_empty_file() -> None:
    response = client.post(
        "/api/resumes/parse",
        files={"file": ("resume.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "上传文件为空。"


def test_reject_unsupported_file_type() -> None:
    response = client.post(
        "/api/resumes/parse",
        files={"file": ("resume.exe", b"content", "application/octet-stream")},
    )

    assert response.status_code == 415


def test_reject_oversized_file(monkeypatch) -> None:
    monkeypatch.setattr(resumes, "MAX_FILE_SIZE", 4)

    response = client.post(
        "/api/resumes/parse",
        files={"file": ("resume.txt", b"12345", "text/plain")},
    )

    assert response.status_code == 413


def test_blank_pdf_suggests_ocr() -> None:
    document = pymupdf.open()
    document.new_page()
    content = document.tobytes()
    document.close()

    response = client.post(
        "/api/resumes/parse",
        files={"file": ("resume.pdf", content, "application/pdf")},
    )

    assert response.status_code == 422
    assert "OCR" in response.json()["detail"]
