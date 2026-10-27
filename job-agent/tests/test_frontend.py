from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_frontend_page_is_available() -> None:
    response = client.get("/upload")

    assert response.status_code == 200
    assert "AI 求职助手" in response.text
    assert "上传测试简历" in response.text
    assert "生成候选人画像" in response.text
    assert 'value="openai"' in response.text
    assert 'value="deepseek"' in response.text
    assert "粘贴岗位描述" in response.text
    assert "简历与岗位匹配度" in response.text
    assert "我的求职看板" in response.text
    assert "第一至第十阶段" in response.text
    assert 'id="application-query"' in response.text
    assert 'id="application-prev"' in response.text
    assert 'id="retain-source-text"' in response.text
    assert "保存岗位与匹配报告" in response.text
    assert 'id="library-panel"' in response.text
    assert 'id="library-reanalyze"' in response.text
    assert 'id="discovery-panel"' in response.text
    assert 'id="discovery-board"' in response.text
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
    assert 'fetch("/api/resumes/analyze"' in js_response.text
    assert 'formData.append("provider"' in js_response.text
    assert 'fetch("/api/jobs/parse"' in js_response.text
    assert 'fetch("/api/matches/analyze"' in js_response.text
    assert 'input[name="match-provider"]:checked' in js_response.text
    assert "选择匹配报告模型" in js_response.text
    assert 'fetch("/api/applications"' in js_response.text
    assert "loadApplications" in js_response.text
    assert "buildDraftEditor" in js_response.text
    assert "核对并确认" in js_response.text
    assert "/draft-versions" in js_response.text
    assert "/sources/status" in js_response.text
    assert "查看字面证据" in js_response.text
    assert "比较两个版本" in js_response.text
    assert "/api/applications/search?" in js_response.text
    assert "/events" in js_response.text
    assert "实际投递日期" in js_response.text
    assert "/api/library/reports/reanalyze" in js_response.text
    assert "/api/library/jobs" in js_response.text
    assert "/api/discovery/search" in js_response.text
    assert "/api/discovery/imports" in js_response.text
