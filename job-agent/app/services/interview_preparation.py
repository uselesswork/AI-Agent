"""仅从已确认版本挑选复习线索，不生成候选人的虚构回答。"""

from app.models.application import ApplicationDetail
from app.models.draft_version import DraftVersionDetail
from app.models.planning import InterviewPreparation, PreparationPrompt


def compose_interview_preparation(
    record: ApplicationDetail, version: DraftVersionDetail,
) -> InterviewPreparation:
    if version.reviewed_at is None:
        raise ValueError("请先人工核对并确认该草稿版本。")
    resume_lines = [line.strip() for section in version.resume.sections
                    for line in section.lines if line.strip()]
    focuses = list(dict.fromkeys(skill.strip()[:120] for skill in
                                 record.job_profile.required_skills if skill.strip()))[:6]
    if not focuses:
        focuses = list(dict.fromkeys(text.strip()[:120] for text in
                                    record.job_profile.responsibilities if text.strip()))[:4]
    prompts: list[PreparationPrompt] = []
    for focus in focuses:
        matching = [line[:240] for line in resume_lines if focus.casefold() in line.casefold()][:3]
        prompts.append(PreparationPrompt(
            question=f"请用真实项目或经历说明你如何运用“{focus}”。",
            focus=focus, reviewed_material_lines=matching, needs_example=not bool(matching),
        ))
    for gap in record.match_result.gaps[:2]:
        focus = gap.strip()[:120]
        if focus:
            prompts.append(PreparationPrompt(
                question=f"如果被问到“{focus}”，你会如何如实说明现状和改进计划？",
                focus=focus, reviewed_material_lines=[], needs_example=True,
            ))
    if not prompts:
        prompts.append(PreparationPrompt(
            question="请根据已确认简历，准备一个与目标岗位有关的真实项目案例。",
            focus="项目经历", reviewed_material_lines=[], needs_example=True,
        ))
    return InterviewPreparation(
        application_id=record.id, version=version.version,
        job_title=record.job_profile.title, company=record.job_profile.company,
        resume_title=version.resume.title, cover_letter_title=version.cover_letter.title,
        prompts=prompts,
        checklist=[
            "重新阅读原招聘页，核对岗位要求和面试时间、地点或会议链接。",
            "对照已确认简历和求职信，挑选确实做过的案例；不要把岗位要求当作个人经历。",
            "对匹配报告中的差距逐项核对，准备如实说明与学习计划；报告判断可能有误。",
            "面试结束后自行记录进展，并在日程中标记已完成或安排后续跟进。",
        ],
    )
