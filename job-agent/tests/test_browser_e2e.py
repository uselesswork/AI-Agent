"""真实浏览器全链路：独立 SQLite、虚构资料、不调用模型或现有 MySQL。"""

import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from app.api import applications, discovery, library
from app.core.user_scope import bind_user, reset_user
from app.main import app
from app.models.application import ApplicationCreate
from app.services.application_repository import ApplicationRepository
from app.services.auth_repository import AuthRepository
from tests.test_applications_api import application_payload

PASSWORD = "BrowserFixturePassphrase-A1"
RESUME_FILE = Path(__file__).parents[2] / "test" / "测试简历模板.txt"


@pytest.fixture
def local_server(monkeypatch, tmp_path):
    database = (tmp_path / "browser.db").as_posix()
    repository = ApplicationRepository(f"sqlite+pysqlite:///{database}")
    monkeypatch.setattr(applications, "get_repository", lambda: repository)
    monkeypatch.setattr(library, "get_repository", lambda: repository)
    monkeypatch.setattr(discovery, "get_repository", lambda: repository)
    accounts = AuthRepository(repository.engine)
    user_id = accounts.create_user("browser_owner", PASSWORD)
    accounts.create_user("other_owner", "OtherBrowserPassphrase-B1")
    token = bind_user(user_id)
    try:
        repository.create(ApplicationCreate.model_validate(application_payload()))
    finally:
        reset_user(token)

    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port,
                            log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("隔离浏览器测试服务未能启动。")
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        repository.engine.dispose()


@pytest.mark.auth_real
@pytest.mark.browser_e2e
def test_login_resume_parse_dashboard_isolation_and_logout(local_server) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as browser_tool:
        launch = {"headless": True}
        edge = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
        channel = os.environ.get("JOB_AGENT_BROWSER_CHANNEL")
        if channel:
            launch["channel"] = channel
        elif edge.exists():
            launch["channel"] = "msedge"
        browser = browser_tool.chromium.launch(**launch)
        try:
            context = browser.new_context(locale="zh-CN")
            page = context.new_page()
            page.goto(f"{local_server}/upload")
            assert page.locator("#auth-gate").is_visible()
            assert page.locator("#page-shell").get_attribute("inert") is not None
            page.locator("#login-username").fill("browser_owner")
            page.locator("#login-password").fill(PASSWORD)
            page.locator("#login-form button[type=submit]").click()
            page.locator("#account-name").get_by_text("当前账号：browser_owner").wait_for()
            page.locator(".application-card").get_by_text("星云科技").wait_for()
            page.locator("#resume-file").set_input_files(str(RESUME_FILE))
            page.locator("#parse-button").click()
            page.locator("#result-content").wait_for(state="visible")
            assert "测试" in page.locator("#resume-text").inner_text()

            other_context = browser.new_context(locale="zh-CN")
            other_page = other_context.new_page()
            other_page.goto(f"{local_server}/upload")
            other_page.locator("#login-username").fill("other_owner")
            other_page.locator("#login-password").fill("OtherBrowserPassphrase-B1")
            other_page.locator("#login-form button[type=submit]").click()
            other_page.locator("#account-name").get_by_text("当前账号：other_owner").wait_for()
            assert other_page.locator(".application-card").count() == 0

            page.locator("#logout-button").click()
            page.locator("#auth-gate").wait_for(state="visible")
            assert page.locator("#page-shell").get_attribute("inert") is not None
            other_context.close()
            context.close()
        finally:
            browser.close()
