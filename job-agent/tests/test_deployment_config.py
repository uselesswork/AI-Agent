"""部署文件静态检查；不等同于实际容器构建和运行。"""

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_compose_is_local_only_and_checks_readiness() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    service = compose["services"]["app"]
    assert service["ports"] == ["127.0.0.1:8000:8000"]
    assert service["env_file"] == ".env.docker"
    assert service["read_only"] is True
    assert "/ready" in service["healthcheck"]["test"][-1]


def test_image_does_not_embed_env_or_run_as_root() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "USER jobagent" in dockerfile
    assert "--no-access-log" in dockerfile
    assert ".env" in ignore
    assert "COPY . " not in dockerfile
