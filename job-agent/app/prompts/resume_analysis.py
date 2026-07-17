import json

from app.models.candidate import CandidateProfile

SYSTEM_PROMPT = """你是严谨的中文简历信息抽取器。你的唯一任务是把简历正文转换为 JSON 候选人画像。

必须遵守以下规则：
1. 只能使用简历明确提供的信息，不得推测、补全或美化。
2. 缺失的单值字段使用 null，缺失的列表使用 []。
3. 日期保留简历原始精度，不要虚构具体日期。
4. 技能熟练度只有在原文明确说明时才能填写，否则为 null。
5. evidence.quote 必须逐字引用简历原文，不能改写；找不到证据时保留空列表并在 warnings 中说明。
6. 将奖项、证书和语言考试放入 certificates。
7. 输出必须是一个合法 JSON 对象，不要输出 Markdown、解释或代码块。
"""


def build_resume_analysis_prompt(resume_text: str) -> str:
    schema = json.dumps(
        CandidateProfile.model_json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    example = {
        "basic_info": {
            "name": "示例姓名",
            "email": None,
            "phone": None,
            "location": None,
            "links": [],
        },
        "job_targets": [],
        "summary": None,
        "education": [],
        "skills": [],
        "projects": [],
        "experiences": [],
        "certificates": [],
        "warnings": ["简历中未找到电子邮箱"],
    }
    return (
        "请根据下面的 JSON Schema 输出候选人画像。字段名称和类型必须严格匹配。\n"
        f"JSON Schema：{schema}\n"
        f"最小 JSON 示例：{json.dumps(example, ensure_ascii=False)}\n\n"
        "简历正文开始：\n"
        f"{resume_text}\n"
        "简历正文结束。"
    )
