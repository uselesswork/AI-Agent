"""显式 live 评估的最小 JSONL 用量日志与 Hub 重试。"""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.services.call_metadata import ModelCallMetadata


def append_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def record_call(
    path: Path, evaluation_run_id: str, case_id: str, provider: str,
    call: ModelCallMetadata, price_version: str | None = None,
) -> None:
    payload = {
        "requestId": call.request_id,
        "modelId": call.model_id,
        "latencyMs": call.latency_ms,
    }
    if call.input_tokens is not None and call.output_tokens is not None:
        payload.update(inputTokens=call.input_tokens, outputTokens=call.output_tokens)
    if price_version:
        payload["priceVersion"] = price_version
    append_event(path, {
        "type": "call", "evaluationRunId": evaluation_run_id,
        "caseId": case_id, "provider": provider, "payload": payload,
    })


def pending_calls(path: Path, hub_run_id: str) -> list[dict]:
    calls: list[dict] = []
    sent: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["type"] == "call":
            calls.append(event)
        elif event["type"] == "sent" and event["hubRunId"] == hub_run_id:
            sent.add(event["requestId"])
    return [call for call in calls if call["payload"]["requestId"] not in sent]


def _matching_duplicate(url: str, payload: dict) -> bool:
    request = Request(url, method="GET")
    with urlopen(request, timeout=5) as response:
        usage = json.load(response)
    fields = ("requestId", "modelId", "latencyMs", "inputTokens", "outputTokens", "priceVersion")
    return any(
        all(call.get(key) == payload.get(key) for key in fields)
        for call in usage.get("calls", [])
        if call.get("requestId") == payload["requestId"]
    )


def upload_pending(path: Path, hub_url: str, hub_run_id: str) -> tuple[int, int]:
    base = f"{hub_url.rstrip('/')}/api/runs/{hub_run_id}"
    sent = 0
    failed = 0
    for event in pending_calls(path, hub_run_id):
        payload = event["payload"]
        if not payload.get("modelId"):
            failed += 1
            continue
        request = Request(
            f"{base}/calls", data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        accepted = False
        try:
            with urlopen(request, timeout=5) as response:
                accepted = response.status == 201
        except HTTPError as exc:
            if exc.code == 409:
                try:
                    accepted = _matching_duplicate(f"{base}/usage", payload)
                except (HTTPError, URLError, ValueError, OSError, TypeError, AttributeError):
                    pass
        except (URLError, OSError):
            pass
        if accepted:
            append_event(path, {
                "type": "sent", "hubRunId": hub_run_id,
                "requestId": payload["requestId"],
            })
            sent += 1
        else:
            failed += 1
    return sent, failed
