from io import BytesIO
from pathlib import Path

import pymupdf
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select

from app.api import applications
from app.core.database_schema import draft_versions
from app.main import app
from app.services.application_repository import ApplicationRepository
from tests.test_applications_api import application_payload, use_temporary_repository

client = TestClient(app)


def _create_application() -> int:
    response = client.post("/api/applications", json=application_payload())
    assert response.status_code == 201
    return response.json()["id"]


def _edited_documents(record_id: int) -> dict:
    result = client.get(f"/api/applications/{record_id}/draft").json()
    result["resume"]["title"] = "张晨的人工定稿"
    result["resume"]["sections"][0]["lines"].append("经本人核对的联系信息")
    result["cover_letter"]["sections"][1]["lines"] = ["这是本人编辑的求职意向。"]
    return {"resume": result["resume"], "cover_letter": result["cover_letter"]}


def test_versions_are_immutable_and_review_controls_download(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    record_id = _create_application()
    documents = _edited_documents(record_id)
    base = f"/api/applications/{record_id}/draft-versions"

    first = client.post(base, json=documents)
    assert first.status_code == 201
    assert first.json()["version"] == 1
    assert first.json()["reviewed_at"] is None
    assert client.get(f"{base}/1/resume.docx").status_code == 409
    assert client.patch(f"{base}/1/review", json={"confirmed": False}).status_code == 422

    reviewed = client.patch(f"{base}/1/review", json={"confirmed": True})
    assert reviewed.status_code == 200
    reviewed_at = reviewed.json()["reviewed_at"]
    assert reviewed_at
    assert client.patch(f"{base}/1/review", json={"confirmed": True}).json()[
        "reviewed_at"] == reviewed_at

    docx_response = client.get(f"{base}/1/resume.docx")
    assert docx_response.status_code == 200
    docx = Document(BytesIO(docx_response.content))
    assert any("经本人核对的联系信息" in p.text for p in docx.paragraphs)
    pdf_response = client.get(f"{base}/1/letter.pdf")
    assert pdf_response.status_code == 200
    with pymupdf.open(stream=pdf_response.content, filetype="pdf") as pdf:
        assert "这是本人编辑的求职意向" in "".join(page.get_text() for page in pdf)

    documents["resume"]["title"] = "第二版人工定稿"
    second = client.post(base, json=documents)
    assert second.status_code == 201
    assert second.json()["version"] == 2
    assert second.json()["reviewed_at"] is None
    assert client.get(f"{base}/2/resume.pdf").status_code == 409
    assert client.get(f"{base}/1").json()["resume"]["title"] == "张晨的人工定稿"
    assert [row["version"] for row in client.get(base).json()] == [2, 1]


def test_version_is_scoped_to_application(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    first_id = _create_application()
    second_id = _create_application()
    assert client.post(f"/api/applications/{first_id}/draft-versions",
                       json=_edited_documents(first_id)).status_code == 201
    assert client.get(f"/api/applications/{second_id}/draft-versions/1").status_code == 404
    assert client.patch(f"/api/applications/{second_id}/draft-versions/1/review",
                        json={"confirmed": True}).status_code == 404
    assert client.get("/api/applications/999/draft-versions").status_code == 404
    assert client.post("/api/applications/999/draft-versions",
                       json=_edited_documents(first_id)).status_code == 404


def test_invalid_draft_version_is_rejected(monkeypatch, tmp_path: Path) -> None:
    use_temporary_repository(monkeypatch, tmp_path)
    record_id = _create_application()
    documents = _edited_documents(record_id)
    documents["resume"]["sections"] = []
    assert client.post(f"/api/applications/{record_id}/draft-versions",
                       json=documents).status_code == 422
    documents = _edited_documents(record_id)
    documents["resume"]["sections"][0]["lines"] = ["字" * 3001]
    assert client.post(f"/api/applications/{record_id}/draft-versions",
                       json=documents).status_code == 422


def test_deleting_application_cascades_draft_versions(monkeypatch, tmp_path: Path) -> None:
    repo = ApplicationRepository(f"sqlite+pysqlite:///{(tmp_path / 'cascade.db').as_posix()}")
    repo.engine.dispose()

    @event.listens_for(repo.engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    monkeypatch.setattr(applications, "get_repository", lambda: repo)
    record_id = _create_application()
    assert client.post(f"/api/applications/{record_id}/draft-versions",
                       json=_edited_documents(record_id)).status_code == 201
    assert client.delete(f"/api/applications/{record_id}").status_code == 204
    with repo.engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(draft_versions)) == 0
    repo.engine.dispose()
