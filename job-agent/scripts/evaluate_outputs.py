"""评估虚构夹具输出；显式 --live 时才调用所选模型服务商。"""

import argparse
import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit
from uuid import uuid4

from app.core.config import get_settings
from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.services.evaluation import evaluate_case
from app.services.job_analyzer import build_job_analyzer
from app.services.match_analyzer import build_match_analyzer
from app.services.resume_analyzer import build_resume_analyzer
from app.services.call_metadata import observe_model_calls
from scripts.live_usage import record_call, upload_pending
from scripts.hub_report import save_report, upload_report

DEFAULT_CASES = Path(__file__).parents[1] / "evals" / "cases.json"


async def generate_live(case: dict, provider: str) -> dict:
    task = case["task"]
    if task == "resume":
        result = await build_resume_analyzer(provider).analyze(case["source_resume"])
    elif task == "job":
        result = await build_job_analyzer(provider).analyze(case["source_job"])
    else:
        candidate = CandidateProfile.model_validate(case["candidate_profile"])
        job = JobProfile.model_validate(case["job_profile"])
        result = await build_match_analyzer(provider).analyze(candidate, job)
    return result.model_dump(mode="json")


def load_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("评估文件须为非空 JSON 数组。")
    seen: set[str] = set()
    for case in data:
        if not isinstance(case, dict) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",
                                                        str(case.get("id", ""))):
            raise ValueError("每个用例须有由字母、数字、下划线或连字符组成的 ID。")
        if case["id"] in seen:
            raise ValueError("评估用例 ID 不能重复。")
        seen.add(case["id"])
        if case.get("task") not in {"resume", "job", "match"}:
            raise ValueError("评估任务只能是 resume、job 或 match。")
    return data


def summarize_results(results: list[dict]) -> dict:
    """只汇总规则检查，不把离线夹具通过率称为模型准确率。"""
    checks = [check for result in results for check in result["checks"]]

    def rate(names: set[str]) -> str:
        selected = [check for check in checks if check["name"] in names]
        return f"{sum(check['passed'] for check in selected)}/{len(selected)}" if selected else "无样本"

    hard_names = {"expected_required_skills", "no_unsupported_required_skills",
                  "expected_job_requirements", "expected_requirements",
                  "expected_assessment_statuses"}
    return {
        "structure": rate({"schema_valid"}),
        "evidence": rate({"resume_evidence_literal", "job_evidence_literal",
                          "match_resume_evidence_literal", "match_job_evidence_literal"}),
        "hard_condition_misses": sum(not check["passed"] for check in checks
                                     if check["name"] in hard_names),
        "score_consistency": rate({"weighted_score_near_overall"}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="用虚构案例检查模型输出结构与字面证据。")
    parser.add_argument("--file", type=Path, default=DEFAULT_CASES, help="用例 JSON 路径")
    parser.add_argument("--live", action="store_true", help="显式调用真实模型，可能产生费用")
    parser.add_argument("--provider", choices=("openai", "deepseek"), help="真实模型服务商")
    parser.add_argument("--usage-file", type=Path, help="live 用量 JSONL 路径；默认生成独立文件")
    parser.add_argument("--retry-usage-file", type=Path, help="只重试本地 JSONL 的待上报调用")
    parser.add_argument("--report-file", type=Path, help="Hub 规则报告 JSON；默认生成独立文件")
    parser.add_argument("--retry-report-file", type=Path, help="只重传已有报告，不运行模型")
    parser.add_argument("--hub-url", help="显式启用 Hub 上报的服务地址")
    parser.add_argument("--hub-run-id", help="Hub 中已存在的运行 ID")
    parser.add_argument("--price-version", help="明确登记的价格版本；未指定则省略")
    args = parser.parse_args()
    if args.hub_run_id and not args.hub_url:
        parser.error("--hub-run-id 需要 --hub-url。")
    if args.hub_url:
        parsed = urlsplit(args.hub_url)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            parser.error("--hub-url 必须是 HTTP(S) 服务根地址。")
        if args.hub_run_id and not re.fullmatch(r"[0-9a-fA-F-]{36}", args.hub_run_id):
            parser.error("--hub-run-id 必须是 Hub 运行 UUID。")
    if args.retry_report_file:
        if args.live or args.provider or args.report_file or args.usage_file or not args.hub_url or args.hub_run_id:
            parser.error("报告重试只接受 --retry-report-file、可选 --retry-usage-file 和 --hub-url。")
        try:
            run_id = upload_report(args.retry_report_file, args.hub_url)
            sent, failed = upload_pending(args.retry_usage_file, args.hub_url, run_id) if args.retry_usage_file else (0, 0)
        except (OSError, ValueError, KeyError, RuntimeError):
            print("Hub 报告或用量重试失败；本地文件仍在。")
            return 2
        print(f"Hub 运行 {run_id}；调用已送达 {sent} 条，仍待重试 {failed} 条。")
        return 0 if failed == 0 else 2
    if args.retry_usage_file:
        if args.live or args.provider or args.usage_file or args.price_version or not args.hub_url or not args.hub_run_id:
            parser.error("重试模式仅接受 --retry-usage-file、--hub-url 和 --hub-run-id。")
        try:
            sent, failed = upload_pending(args.retry_usage_file, args.hub_url, args.hub_run_id)
        except (OSError, ValueError, KeyError):
            print("无法读取用量 JSONL；未发送调用。")
            return 2
        print(f"上报成功或已确认重复：{sent}；仍待重试：{failed}。")
        return 0 if failed == 0 else 2
    if args.live != bool(args.provider):
        parser.error("真实评估必须同时提供 --live 和 --provider；默认仅检查夹具。")
    if not args.live and (args.usage_file or args.price_version or args.hub_run_id):
        parser.error("用量记录及手动 Hub 运行 ID 仅允许显式 --live 评估。")
    if args.report_file and not args.hub_url:
        parser.error("--report-file 需要 --hub-url。")
    try:
        cases = load_cases(args.file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"无法读取评估用例：{type(exc).__name__}。")
        return 2
    evaluation_run_id = uuid4().hex if args.live else None
    source_run_id = evaluation_run_id or uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat()
    usage_file = args.usage_file or (Path("test-results/live-usage") / f"{evaluation_run_id}.jsonl") if args.live else None
    if usage_file is not None and usage_file.exists():
        parser.error("本次 live 用量文件已存在；请使用新路径，旧文件通过重试入口上报。")
    results = []
    for case in cases:
        started = perf_counter() if args.live else None
        try:
            if args.live:
                with observe_model_calls(lambda call, case_id=case["id"]: record_call(
                    usage_file, evaluation_run_id, case_id, args.provider, call, args.price_version
                )):
                    output = asyncio.run(generate_live(case, args.provider))
            else:
                output = case["output"]
            result = evaluate_case(case, output)
        except Exception:
            # 模型/网络异常可能含私密请求内容；只输出用例 ID 和失败类型。
            result = {"id": case["id"], "task": case["task"], "passed": False,
                      "checks": [{"name": "generation_or_case_error", "passed": False}]}
        results.append(result)
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        print(f"{result['id']}: {'通过' if result['passed'] else '未通过'}"
              + (f"；检查项：{', '.join(failed)}" if failed else ""))
        if started is not None:
            print(f"  耗时：{perf_counter() - started:.2f} 秒")
    passed = sum(item["passed"] for item in results)
    summary = summarize_results(results)
    print(f"合计：{passed}/{len(results)} 通过；模式：{'真实模型' if args.live else '离线夹具'}。")
    print(f"结构通过：{summary['structure']}；字面证据检查：{summary['evidence']}；"
          f"硬性条件漏判检查失败：{summary['hard_condition_misses']}；"
          f"评分一致性：{summary['score_consistency']}。")
    if args.hub_url and not args.hub_run_id:
        model = None
        if args.live:
            settings = get_settings()
            model = settings.openai_model if args.provider == "openai" else settings.deepseek_model
        report_file = args.report_file or (Path("test-results/job-reports") / f"{source_run_id}.json")
        report = {"sourceRunId": source_run_id,
                  "datasetSha256": hashlib.sha256(args.file.read_bytes()).hexdigest(),
                  "runLabel": f"job-eval-{source_run_id[:12]}",
                  "resultSource": "LIVE_MODEL" if args.live else "OFFLINE_FIXTURE",
                  "modelId": model, "startedAt": started_at,
                  "cases": [{"id": item["id"], "task": item["task"],
                             "passed": item["passed"], "checks": item["checks"]}
                            for item in results]}
        try:
            save_report(report_file, report)
            run_id = upload_report(report_file, args.hub_url)
        except (OSError, ValueError, KeyError, RuntimeError):
            print(f"Hub 报告上报失败；本地报告在 {report_file}，可用 --retry-report-file 重试。")
            return 2
        print(f"Hub 评测运行：{run_id}；本地规则报告：{report_file}。")
        if args.live and usage_file.exists():
            sent, failed = upload_pending(usage_file, args.hub_url, run_id)
            print(f"Hub 调用已送达：{sent}；待重试：{failed}。")
            if failed:
                return 2
    if args.live:
        settings = get_settings()
        model = settings.openai_model if args.provider == "openai" else settings.deepseek_model
        print(f"模型配置：{args.provider}/{model}；本地用量文件：{usage_file}；费用由 Hub 独立核算。")
        if args.hub_url and args.hub_run_id:
            sent, failed = upload_pending(usage_file, args.hub_url, args.hub_run_id) if usage_file.exists() else (0, 0)
            print(f"Hub 上报成功或已确认重复：{sent}；待重试：{failed}。")
            if failed:
                print("可用 --retry-usage-file、--hub-url 和 --hub-run-id 重试，requestId 保持不变。")
                return 2
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
