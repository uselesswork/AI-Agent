import json

from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.models.match import MatchResult

SYSTEM_PROMPT = """你是基于证据的实习岗位匹配分析器。
只能依据输入的候选人画像和岗位画像评分，不得编造候选人经历。
评分固定包含五个维度，权重分别为：技能匹配 35、项目经验 25、教育背景 15、实习经历 15、基本条件 10。
overall_score 应与维度加权分一致，四舍五入为整数。
每个岗位要求都要给出判断；无法从简历确认时必须标记“无法确认”。
简历建议只能调整表达、顺序或补充真实信息，禁止建议伪造经历。
输出合法 JSON 对象，不要输出 Markdown、解释或代码块。"""


def build_match_analysis_prompt(candidate: CandidateProfile, job: JobProfile) -> str:
    schema = json.dumps(MatchResult.model_json_schema(), ensure_ascii=False, separators=(",", ":"))
    candidate_json = candidate.model_dump_json(exclude_none=False)
    job_json = job.model_dump_json(exclude_none=False)
    return (
        f"请严格按照 JSON Schema 输出匹配结果。\nJSON Schema：{schema}\n"
        f"候选人画像：{candidate_json}\n岗位画像：{job_json}"
    )
