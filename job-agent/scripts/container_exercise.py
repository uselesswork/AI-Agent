"""在隔离 Compose 项目中演练建库、登录、投递、重启和清理。"""

import http.cookiejar
import json
import os
import secrets
import subprocess
import time
import urllib.request

BASE_URL = "http://127.0.0.1:18080"


def _request(path: str, opener=None) -> tuple[int, bytes]:
    target = BASE_URL + path
    if opener is None:
        response = urllib.request.urlopen(target, timeout=10)
    else:
        response = opener.open(target, timeout=10)
    with response:
        return response.status, response.read()


def _post(path: str, payload: dict, opener, csrf: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if csrf:
        headers["X-CSRF-Token"] = csrf
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=headers,
        method="POST",
    )
    with opener.open(request, timeout=15) as response:
        return response.status, json.load(response)


def _application_payload() -> dict:
    dimensions = [
        {"name": name, "score": 50, "weight": weight, "reason": "演练"}
        for name, weight in [
            ("技能匹配", 35), ("项目经验", 25), ("教育背景", 15),
            ("实习经历", 15), ("基本条件", 10),
        ]
    ]
    return {
        "resume_filename": "演练简历.txt",
        "candidate_profile": {"basic_info": {"name": "虚构候选人"}},
        "job_profile": {"title": "测试实习岗位", "company": "虚构企业"},
        "match_result": {
            "overall_score": 50, "recommendation": "谨慎投递",
            "summary": "仅用于容器演练", "dimensions": dimensions,
        },
        "provider": "openai", "model": "exercise-fixture", "status": "待投递",
    }


def main() -> int:
    project = "jobagentexercise" + secrets.token_hex(3)
    environment = os.environ.copy()
    environment["JOB_AGENT_EXERCISE_ROOT_PASSWORD"] = secrets.token_hex(16)
    environment["JOB_AGENT_EXERCISE_DB_PASSWORD"] = secrets.token_hex(16)
    environment["JOB_AGENT_EXERCISE_LOGIN_PASSWORD"] = secrets.token_hex(16)
    compose = ["docker", "compose", "-f", "compose.exercise.yaml", "-p", project]

    def step(name: str, args: list[str], timeout: int = 180) -> str:
        print(name, flush=True)
        result = subprocess.run(compose + args, env=environment, capture_output=True,
                                text=True, timeout=timeout, check=False)
        if result.returncode:
            print(f"失败步骤：{name}；退出码：{result.returncode}", flush=True)
            raise RuntimeError(name)
        return result.stdout

    started = time.perf_counter()
    try:
        step("校验 Compose 配置", ["config", "--quiet"])
        step("构建项目镜像", ["build", "app"], timeout=300)
        build_seconds = round(time.perf_counter() - started, 1)
        step("启动隔离 MySQL", ["up", "-d", "--wait", "mysql"])
        migration = step("从迁移链初始化空库", [
            "run", "--rm", "--no-deps", "app", "python", "-m",
            "scripts.manage_migrations", "initialize",
        ])
        if "0002_user_assets_owner_index" not in migration:
            raise RuntimeError("迁移未到预期版本")
        create_user_code = (
            "import os; from sqlalchemy import create_engine; "
            "from app.core.config import get_settings; "
            "from app.services.auth_repository import AuthRepository; "
            "engine=create_engine(get_settings().validated_database_url()); "
            "AuthRepository(engine).create_user('exercise_owner', "
            "os.environ['JOB_AGENT_EXERCISE_LOGIN_PASSWORD']); engine.dispose()"
        )
        step("创建虚构登录账号", ["run", "--rm", "--no-deps",
                                 "-e", "JOB_AGENT_EXERCISE_LOGIN_PASSWORD", "app",
                                 "python", "-c", create_user_code])
        step("启动应用并等待健康", ["up", "-d", "--no-build", "--wait", "app"])

        for path in ("/health", "/ready", "/upload", "/static/app.js"):
            status, _ = _request(path)
            if status != 200:
                raise RuntimeError(f"{path} 返回 {status}")
            print(f"{path}: 200", flush=True)

        cookies = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
        status, account = _post("/api/auth/login", {
            "username": "exercise_owner",
            "password": environment["JOB_AGENT_EXERCISE_LOGIN_PASSWORD"],
        }, opener)
        if status != 200:
            raise RuntimeError("虚构账号登录失败")
        status, created = _post("/api/applications", _application_payload(), opener,
                                account["csrf_token"])
        if status != 201:
            raise RuntimeError("投递写入失败")
        record_id = created["id"]

        def check_record() -> None:
            status, body = _request("/api/applications", opener)
            if status != 200 or not any(item["id"] == record_id for item in json.loads(body)):
                raise RuntimeError("持久化投递读取失败")

        check_record()
        print("登录、投递写入与重新读取: 通过", flush=True)
        marker = "query_marker_" + secrets.token_hex(4)
        _request("/health?" + marker)
        step("停止应用容器", ["stop", "app"])
        step("重启应用容器", ["up", "-d", "--no-build", "--wait", "app"])
        check_record()
        print("重启后读取同一投递: 通过", flush=True)

        logs = step("检查应用日志", ["logs", "--no-color", "app"])
        if (marker in logs or environment["JOB_AGENT_EXERCISE_LOGIN_PASSWORD"] in logs
                or "演练简历.txt" in logs
                or any(cookie.value in logs for cookie in cookies)):
            raise RuntimeError("应用日志出现测试敏感值")
        print("日志敏感值检查: 通过", flush=True)
        image = subprocess.run(["docker", "image", "inspect", "job-agent-exercise:local",
                                "--format", "{{.Size}}"], capture_output=True,
                               text=True, check=True)
        print(f"镜像大小：{int(image.stdout.strip()) / 1_000_000:.1f} MB", flush=True)
        print(f"构建耗时：{build_seconds:.1f} 秒", flush=True)
        return 0
    finally:
        result = subprocess.run(compose + ["down", "-v", "--remove-orphans"],
                                env=environment, capture_output=True, text=True,
                                timeout=180, check=False)
        print(f"隔离容器和数据卷清理退出码：{result.returncode}", flush=True)
        print(f"演练项目：{project}", flush=True)
        if result.returncode:
            raise RuntimeError("隔离容器和数据卷清理失败")


if __name__ == "__main__":
    raise SystemExit(main())
