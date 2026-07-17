import json

from app.models.job import JobProfile

SYSTEM_PROMPT = """你是严谨的实习岗位描述解析器。只能使用岗位原文，不得推测。
提取岗位职责、技能和基本要求。每项 requirement 的 evidence 必须逐字引用岗位原文。
必须区分“必须”和“加分”；原文没有说明的信息使用 null 或空列表。
输出合法 JSON 对象，不要输出 Markdown、解释或代码块。"""


def build_job_analysis_prompt(description: str) -> str:
    schema = json.dumps(JobProfile.model_json_schema(), ensure_ascii=False, separators=(",", ":"))
    return f"请严格按照 JSON Schema 解析岗位描述。\nJSON Schema：{schema}\n岗位描述：\n{description}"
