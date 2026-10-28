"""模型输出的可复现规则评估；只检查结构和字面证据，不声称事实核验。"""

from typing import Any

from pydantic import ValidationError

from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.models.match import MatchResult

MODELS = {"resume": CandidateProfile, "job": JobProfile, "match": MatchResult}


def _plain(text: str) -> str:
    return "".join(character.casefold() for character in text if not character.isspace())


def _in_source(quote: str, source: str) -> bool:
    needle = _plain(quote)
    return bool(needle) and needle in _plain(source)


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": passed}


def evaluate_case(case: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    """返回不含原文的检查结果；未通过项供人工进一步复核。"""
    task = case.get("task")
    if task not in MODELS:
        raise ValueError("评估任务只能是 resume、job 或 match。")
    checks: list[dict[str, Any]] = []
    try:
        model = MODELS[task].model_validate(output)
    except ValidationError:
        checks.append(_check("schema_valid", False))
        return {"id": case.get("id"), "task": task, "passed": False, "checks": checks}
    checks.append(_check("schema_valid", True))
    expected = case.get("expected", {})

    if task == "resume":
        source = case.get("source_resume", "")
        evidence = [item.quote for collection in (
            model.education, model.skills, model.projects,
            model.experiences, model.certificates,
        ) for entry in collection for item in entry.evidence]
        checks.append(_check("resume_evidence_literal",
                             all(_in_source(quote, source) for quote in evidence)))
        if "min_evidence" in expected:
            checks.append(_check("minimum_resume_evidence",
                                 len(evidence) >= expected["min_evidence"]))
        if "skills" in expected:
            names = {item.name.casefold() for item in model.skills}
            checks.append(_check("expected_skills", all(
                skill.casefold() in names for skill in expected["skills"])))
    elif task == "job":
        source = case.get("source_job", "")
        checks.append(_check("job_evidence_literal", all(
            _in_source(item.evidence, source) for item in model.requirements)))
        if "min_requirements" in expected:
            checks.append(_check("minimum_job_requirements",
                                 len(model.requirements) >= expected["min_requirements"]))
        if "required_skills" in expected:
            names = {skill.casefold() for skill in model.required_skills}
            checks.append(_check("expected_required_skills", all(
                skill.casefold() in names for skill in expected["required_skills"])))
    else:
        resume_source = case.get("source_resume", "")
        job_source = case.get("source_job", "")
        checks.append(_check("match_resume_evidence_literal", all(
            _in_source(quote, resume_source)
            for item in model.assessments for quote in item.resume_evidence)))
        checks.append(_check("match_job_evidence_literal", all(
            _in_source(item.job_evidence, job_source)
            for item in model.assessments if item.job_evidence)))
        weighted = sum(item.score * item.weight for item in model.dimensions) / 100
        tolerance = expected.get("score_tolerance", 10)
        checks.append(_check("weighted_score_near_overall",
                             abs(model.overall_score - weighted) <= tolerance))
        if "recommendation" in expected:
            checks.append(_check("expected_recommendation",
                                 model.recommendation == expected["recommendation"]))
        if "requirements" in expected:
            assessed = {item.requirement.casefold() for item in model.assessments}
            checks.append(_check("expected_requirements", all(
                name.casefold() in assessed for name in expected["requirements"])))
        if "min_assessments" in expected:
            checks.append(_check("minimum_match_assessments",
                                 len(model.assessments) >= expected["min_assessments"]))
    return {"id": case.get("id"), "task": task,
            "passed": all(item["passed"] for item in checks), "checks": checks}
