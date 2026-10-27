from app.models.application import ApplicationDetail
from app.models.draft import ApplicationDraft, DraftDocument, DraftSection, DraftTemplate


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _relevance(text: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if keyword.casefold() in text.casefold())


def compose_draft(record: ApplicationDetail, template: DraftTemplate = "standard") -> ApplicationDraft:
    """只重排已保存的画像事实，不把匹配报告的判断变为简历事实。"""
    candidate, job = record.candidate_profile, record.job_profile
    required = _unique(job.required_skills + job.preferred_skills)
    target = job.title or "目标岗位"
    company = job.company or "招聘团队"
    name = candidate.basic_info.name or "候选人"
    contact = _unique([
        candidate.basic_info.email or "", candidate.basic_info.phone or "",
        candidate.basic_info.location or "", *candidate.basic_info.links,
    ])
    skills = sorted(candidate.skills, key=lambda item: _relevance(item.name, required),
                    reverse=True)
    projects = sorted(candidate.projects, key=lambda item: _relevance(
        " ".join([item.name, item.description or "", *item.technologies, *item.highlights]),
        required), reverse=True)
    if template == "compact":
        skills = skills[:5]
        projects = projects[:2]
    sections = [DraftSection(heading="基本信息", lines=[name, *contact, f"目标岗位：{target}"])]
    if candidate.summary and template == "standard":
        sections.append(DraftSection(heading="个人简介（原画像）", lines=[candidate.summary]))
    if candidate.education:
        lines = []
        for item in candidate.education:
            lines.append(" · ".join(filter(None, [item.institution, item.degree, item.major,
                                               "—".join(filter(None, [item.start_date,
                                                                       item.end_date]))])))
            if item.courses and template == "standard":
                lines.append(f"相关课程：{', '.join(item.courses)}")
            if item.gpa and template == "standard":
                lines.append(f"绩点：{item.gpa}")
        sections.append(DraftSection(heading="教育经历", lines=lines))
    if skills:
        sections.append(DraftSection(heading="技能", lines=[
            " · ".join(filter(None, [item.name, item.level])) for item in skills
        ]))
    if projects:
        lines = []
        for item in projects:
            lines.append(" · ".join(filter(None, [item.name, item.role,
                                                "—".join(filter(None, [item.start_date,
                                                                        item.end_date]))])))
            if item.description and template == "standard":
                lines.append(item.description)
            lines.extend(item.highlights if template == "standard" else item.highlights[:2])
            if item.technologies and template == "standard":
                lines.append(f"技术：{', '.join(item.technologies)}")
        sections.append(DraftSection(heading="项目经历", lines=lines))
    if candidate.experiences:
        lines = []
        for item in candidate.experiences:
            lines.append(" · ".join(filter(None, [item.organization, item.role,
                                                "—".join(filter(None, [item.start_date,
                                                                        item.end_date]))])))
            lines.extend(item.highlights if template == "standard" else item.highlights[:2])
        sections.append(DraftSection(heading="实践与实习经历", lines=lines))
    if candidate.certificates and template == "standard":
        sections.append(DraftSection(heading="证书", lines=[
            " · ".join(filter(None, [item.name, item.date])) for item in candidate.certificates
        ]))

    greeting = f"{company}招聘团队：" if job.company else "招聘团队："
    letter = [DraftSection(heading="称呼", lines=[greeting]),
              DraftSection(heading="应聘意向", lines=[
                  f"您好！我是{name}，希望应聘贵团队的{target}岗位。"
              ])]
    evidence_lines = []
    if candidate.education:
        education = candidate.education[0]
        evidence_lines.append("、".join(filter(None, [education.institution,
                                                     education.major, education.degree])))
    if skills:
        evidence_lines.append("技能：" + "、".join(item.name for item in skills[:4]))
    if projects:
        project = projects[0]
        evidence_lines.append("项目：" + project.name)
        if project.description:
            evidence_lines.append(project.description)
    if candidate.experiences:
        experience = candidate.experiences[0]
        evidence_lines.append("实践：" + "、".join(filter(None, [experience.organization,
                                                                experience.role])))
    if evidence_lines:
        letter.append(DraftSection(heading="与岗位相关的已记录事实", lines=evidence_lines))
    letter.append(DraftSection(heading="结尾", lines=[
        "感谢您阅读我的申请。附件为简历，期待进一步交流。", name,
    ]))
    warnings = ["草稿仅根据结构化画像生成，不读取可能另行留存的原始简历和岗位描述；投递前请逐项核对原件。"]
    if template == "compact":
        warnings.append("精简模板只展示部分已记录的技能、项目与经历；省略不代表这些事实不存在。")
    if not evidence_lines:
        warnings.append("画像缺少可用于求职信的教育、技能、项目或实践经历，正文仅保留基本应聘意向。")
    warnings.extend(candidate.warnings)
    return ApplicationDraft(
        template=template,
        resume=DraftDocument(title=f"{name}｜{target}定制简历建议稿", sections=sections),
        cover_letter=DraftDocument(title=f"{target}求职信草稿", sections=letter),
        suggestions=_unique(record.match_result.resume_suggestions),
        warnings=_unique(warnings),
    )
