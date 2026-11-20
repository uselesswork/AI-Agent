"""离线评估夹具及反例；不连接真实模型。"""

from copy import deepcopy
from types import SimpleNamespace

from app.services.evaluation import evaluate_case
from scripts import evaluate_outputs


def _cases():
    return evaluate_outputs.load_cases(evaluate_outputs.DEFAULT_CASES)


def test_fixture_outputs_pass_offline_rules() -> None:
    cases = _cases()
    assert len(cases) == 20
    assert {case["task"] for case in cases} == {"resume", "job", "match"}
    assert all(case["review"]["origin"] == "虚构合成" for case in cases)
    assert all(evaluate_case(case, case["output"])["passed"] for case in cases)


def test_fabricated_resume_quote_is_rejected() -> None:
    case = deepcopy(_cases()[0])
    case["output"]["skills"][0]["evidence"][0]["quote"] = "五年商业项目经验"
    result = evaluate_case(case, case["output"])
    assert not result["passed"]
    assert {item["name"] for item in result["checks"] if not item["passed"]} == {
        "resume_evidence_literal",
    }


def test_missing_required_evidence_is_rejected() -> None:
    case = deepcopy(_cases()[0])
    case["output"]["skills"][0]["evidence"] = []
    case["output"]["projects"][0]["evidence"] = []
    result = evaluate_case(case, case["output"])
    assert not result["passed"]
    assert {item["name"] for item in result["checks"] if not item["passed"]} == {
        "minimum_resume_evidence",
    }


def test_invalid_schema_and_score_mismatch_are_distinguished() -> None:
    case = deepcopy(_cases()[2])
    case["output"]["dimensions"][0]["weight"] = 99
    result = evaluate_case(case, case["output"])
    assert result["checks"] == [{"name": "schema_valid", "passed": False}]

    case = deepcopy(_cases()[2])
    case["output"]["overall_score"] = 10
    result = evaluate_case(case, case["output"])
    assert {item["name"] for item in result["checks"] if not item["passed"]} == {
        "weighted_score_near_overall",
    }


def test_default_cli_never_calls_live_model(monkeypatch, capsys) -> None:
    async def unexpected_call(*_args):
        raise AssertionError("默认评估不能调用模型")

    monkeypatch.setattr(evaluate_outputs, "generate_live", unexpected_call)
    monkeypatch.setattr("sys.argv", ["scripts.evaluate_outputs"])
    assert evaluate_outputs.main() == 0
    output = capsys.readouterr().out
    assert "离线夹具" in output
    assert "结构通过：20/20" in output
    assert "字面证据检查：24/24" in output


def test_unsupported_skill_and_omitted_hard_condition_are_detected() -> None:
    cases = {case["id"]: case for case in _cases()}
    resume = deepcopy(cases["resume_planned_skill"])
    resume["output"]["skills"].append({"name": "Rust", "category": "编程语言"})
    result = evaluate_case(resume, resume["output"])
    assert "no_unsupported_skills" in {
        check["name"] for check in result["checks"] if not check["passed"]
    }

    job = deepcopy(cases["job_duration_gate"])
    job["output"]["requirements"].pop()
    result = evaluate_case(job, job["output"])
    assert "expected_job_requirements" in {
        check["name"] for check in result["checks"] if not check["passed"]
    }


def test_hard_condition_status_and_score_range_are_detected() -> None:
    case = deepcopy(next(case for case in _cases() if case["id"] == "match_degree_unmet"))
    case["output"]["assessments"][0]["status"] = "满足"
    case["output"]["overall_score"] = 70
    result = evaluate_case(case, case["output"])
    failed = {check["name"] for check in result["checks"] if not check["passed"]}
    assert {"expected_assessment_statuses", "expected_score_range",
            "weighted_score_near_overall"}.issubset(failed)
    summary = evaluate_outputs.summarize_results([result])
    assert summary["hard_condition_misses"] == 1
    assert summary["score_consistency"] == "0/1"


def test_live_report_labels_model_and_unavailable_cost_without_network(
    monkeypatch, capsys,
) -> None:
    async def preset_output(case, _provider):
        return case["output"]

    monkeypatch.setattr(evaluate_outputs, "generate_live", preset_output)
    monkeypatch.setattr(evaluate_outputs, "get_settings", lambda: SimpleNamespace(
        openai_model="synthetic-model", deepseek_model="unused",
    ))
    monkeypatch.setattr("sys.argv", ["scripts.evaluate_outputs", "--live", "--provider", "openai"])
    assert evaluate_outputs.main() == 0
    output = capsys.readouterr().out
    assert "模式：真实模型" in output
    assert "模型配置：openai/synthetic-model" in output
    assert "费用由 Hub 独立核算" in output
    assert "耗时：" in output
