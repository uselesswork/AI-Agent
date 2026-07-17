from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_frontend_page_is_available() -> None:
    response = client.get("/upload")

    assert response.status_code == 200
    assert "AI 求职助手" in response.text
    assert "上传测试简历" in response.text
    assert "/api/resumes/parse" not in response.text


def test_root_does_not_serve_frontend() -> None:
    response = client.get("/")

    assert response.status_code == 404


def test_frontend_assets_are_available() -> None:
    css_response = client.get("/static/styles.css")
    js_response = client.get("/static/app.js")

    assert css_response.status_code == 200
    assert "--green" in css_response.text
    assert js_response.status_code == 200
    assert 'fetch("/api/resumes/parse"' in js_response.text
