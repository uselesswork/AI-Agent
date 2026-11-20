"""只用假供应商响应和本机假 Hub 服务验证 live 用量链路。"""

import asyncio
import json
import threading
from copy import deepcopy
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.config import ProviderConfig
from app.services.call_metadata import observe_model_calls
from app.services.llm import OpenAICompatibleClient
from scripts import evaluate_outputs
from scripts.live_usage import pending_calls, record_call, upload_pending


def model_client(provider: str, responses: list[SimpleNamespace]) -> OpenAICompatibleClient:
    config = ProviderConfig(
        provider=provider, api_key="test-only", model="requested-model",
        base_url="https://example.invalid", timeout_seconds=2,
        max_retries=0, max_output_tokens=100,
    )
    client = OpenAICompatibleClient(config)
    client.client.chat.completions.create = AsyncMock(side_effect=responses)
    return client


def response(model: str, usage: object = None) -> SimpleNamespace:
    return SimpleNamespace(
        model=model, usage=usage,
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))],
    )


def test_openai_and_deepseek_map_response_usage_and_multiple_calls(tmp_path) -> None:
    path = tmp_path / "calls.jsonl"
    run_id = "local-evaluation-1"
    for provider in ("openai", "deepseek"):
        client = model_client(provider, [
            response("actual-model-1", SimpleNamespace(prompt_tokens=12, completion_tokens=5)),
            response("actual-model-2", SimpleNamespace(prompt_tokens=3, completion_tokens=8)),
        ])
        with observe_model_calls(lambda call: record_call(path, run_id, "case-1", provider, call)):
            assert asyncio.run(client.generate_json("private system", "private prompt")) == {"ok": True}
            assert asyncio.run(client.generate_json("private system", "private prompt")) == {"ok": True}
        create = client.client.chat.completions.create
        assert create.await_count == 2
        assert "max_completion_tokens" in create.await_args_list[0].kwargs if provider == "openai" else "max_tokens" in create.await_args_list[0].kwargs

    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(events) == 4
    assert len({event["payload"]["requestId"] for event in events}) == 4
    assert [event["payload"]["modelId"] for event in events] == [
        "actual-model-1", "actual-model-2", "actual-model-1", "actual-model-2"
    ]
    assert events[0]["payload"]["inputTokens"] == 12
    assert events[0]["payload"]["outputTokens"] == 5
    assert all(event["payload"]["latencyMs"] >= 0 for event in events)
    assert all(event["evaluationRunId"] == run_id and event["caseId"] == "case-1" for event in events)
    assert "private" not in path.read_text(encoding="utf-8")


def test_missing_or_partial_usage_omits_both_tokens(tmp_path) -> None:
    path = tmp_path / "missing.jsonl"
    client = model_client("openai", [
        response("model-a"),
        response("model-b", SimpleNamespace(prompt_tokens=7, completion_tokens=None)),
    ])
    with observe_model_calls(lambda call: record_call(path, "run", "case", "openai", call)):
        asyncio.run(client.generate_json("system", "user"))
        asyncio.run(client.generate_json("system", "user"))
    payloads = [item["payload"] for item in pending_calls(path, "hub-run")]
    assert len(payloads) == 2
    assert all("inputTokens" not in payload and "outputTokens" not in payload for payload in payloads)


@contextmanager
def fake_hub():
    calls = {}
    state = {"fail": True, "posts": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            state["posts"] += 1
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if state["fail"]:
                self.send_response(503)
            elif body["requestId"] in calls:
                self.send_response(409)
            else:
                calls[body["requestId"]] = body
                self.send_response(201)
            self.end_headers()

        def do_GET(self):
            body = json.dumps({"calls": list(calls.values())}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", calls, state
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_failed_upload_retry_and_verified_409(tmp_path) -> None:
    path = tmp_path / "calls.jsonl"
    client = model_client("deepseek", [response("actual-deepseek", SimpleNamespace(
        prompt_tokens=0, completion_tokens=4,
    ))])
    with observe_model_calls(lambda call: record_call(path, "eval-run", "case-a", "deepseek", call)):
        asyncio.run(client.generate_json("system", "user"))
    run_id = "11111111-1111-1111-1111-111111111111"
    with fake_hub() as (url, calls, state):
        assert upload_pending(path, url, run_id) == (0, 1)
        assert len(pending_calls(path, run_id)) == 1
        state["fail"] = False
        payload = pending_calls(path, run_id)[0]["payload"]
        calls[payload["requestId"]] = payload.copy()
        assert upload_pending(path, url, run_id) == (1, 0)
        assert pending_calls(path, run_id) == []
        assert upload_pending(path, url, run_id) == (0, 0)
        assert state["posts"] == 2


def test_default_offline_does_not_create_usage_or_upload(tmp_path, monkeypatch) -> None:
    def forbidden(*args):
        raise AssertionError("离线模式不得访问 Hub")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evaluate_outputs, "upload_pending", forbidden)
    monkeypatch.setattr("sys.argv", ["scripts.evaluate_outputs"])
    assert evaluate_outputs.main() == 0
    assert not (tmp_path / "test-results").exists()


def test_conflicting_409_stays_pending(tmp_path) -> None:
    path = tmp_path / "calls.jsonl"
    client = model_client("openai", [response("actual-model")])
    with observe_model_calls(lambda call: record_call(path, "eval", "case", "openai", call)):
        asyncio.run(client.generate_json("system", "user"))
    run_id = "11111111-1111-1111-1111-111111111111"
    with fake_hub() as (url, calls, state):
        state["fail"] = False
        payload = pending_calls(path, run_id)[0]["payload"]
        calls[payload["requestId"]] = {**payload, "modelId": "different-model"}
        assert upload_pending(path, url, run_id) == (0, 1)
        assert len(pending_calls(path, run_id)) == 1


def test_live_cli_collects_two_calls_without_hub(tmp_path, monkeypatch) -> None:
    case = deepcopy(evaluate_outputs.load_cases(evaluate_outputs.DEFAULT_CASES)[0])
    case_file = tmp_path / "case.json"
    case_file.write_text(json.dumps([case], ensure_ascii=False), encoding="utf-8")
    usage_file = tmp_path / "usage.jsonl"
    client = model_client("openai", [response("model-one"), response("model-two")])

    async def fake_generate(selected_case, provider):
        await client.generate_json("system", "user")
        await client.generate_json("system", "user")
        return selected_case["output"]

    def forbidden(*args):
        raise AssertionError("未配置 Hub 时不得上报")

    monkeypatch.setattr(evaluate_outputs, "generate_live", fake_generate)
    monkeypatch.setattr(evaluate_outputs, "upload_pending", forbidden)
    monkeypatch.setattr(evaluate_outputs, "get_settings", lambda: SimpleNamespace(
        openai_model="test-model", deepseek_model="unused"
    ))
    monkeypatch.setattr("sys.argv", [
        "scripts.evaluate_outputs", "--file", str(case_file), "--live", "--provider", "openai",
        "--usage-file", str(usage_file),
    ])
    assert evaluate_outputs.main() == 0
    rows = pending_calls(usage_file, "hub-run")
    assert len(rows) == 2
    assert rows[0]["evaluationRunId"] == rows[1]["evaluationRunId"]
    assert rows[0]["caseId"] == rows[1]["caseId"] == case["id"]
    assert rows[0]["payload"]["requestId"] != rows[1]["payload"]["requestId"]


def test_retry_cli_uses_saved_request_id(tmp_path, monkeypatch) -> None:
    path = tmp_path / "usage.jsonl"
    client = model_client("openai", [response("actual-model")])
    with observe_model_calls(lambda call: record_call(path, "eval", "case", "openai", call)):
        asyncio.run(client.generate_json("system", "user"))
    request_id = pending_calls(path, "hub-run")[0]["payload"]["requestId"]
    run_id = "11111111-1111-1111-1111-111111111111"
    with fake_hub() as (url, calls, state):
        monkeypatch.setattr("sys.argv", [
            "scripts.evaluate_outputs", "--retry-usage-file", str(path),
            "--hub-url", url, "--hub-run-id", run_id,
        ])
        assert evaluate_outputs.main() == 2
        state["fail"] = False
        assert evaluate_outputs.main() == 0
        assert request_id in calls
        assert pending_calls(path, run_id) == []
