"""离线评估夹具及反例；不连接真实模型。"""

from copy import deepcopy

from app.services.evaluation import evaluate_case
from scripts import evaluate_outputs


def _cases():
    return evaluate_outputs.load_cases(evaluate_outputs.DEFAULT_CASES)


def test_fixture_outputs_pass_offline_rules() -> None:
    cases = _cases()
    assert len(cases) == 3
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
    assert "离线夹具" in capsys.readouterr().out
