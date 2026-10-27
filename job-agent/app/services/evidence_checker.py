from difflib import unified_diff

from app.models.annotation import AnnotationDetail
from app.models.draft import DraftDocument
from app.models.draft_version import DraftVersionDetail
from app.models.evidence import EvidenceLine, EvidenceReport, VersionComparison


def _normalized(text: str) -> tuple[str, list[int]]:
    characters: list[str] = []
    positions: list[int] = []
    for index, character in enumerate(text):
        if character.isspace():
            continue
        for folded in character.casefold():
            characters.append(folded)
            positions.append(index)
    return "".join(characters), positions


def _find_excerpt(
    line: str, source_text: str, index: tuple[str, list[int]],
) -> tuple[str, int] | None:
    needle, _ = _normalized(line)
    if len(needle) < 8:
        return None
    haystack, positions = index
    start = haystack.find(needle)
    if start < 0:
        return None
    raw_start = positions[start]
    raw_end = positions[start + len(needle) - 1] + 1
    return source_text[max(0, raw_start - 30):min(len(source_text), raw_end + 30)], raw_start


def literal_in_source(quote: str, source_text: str) -> bool:
    needle, _ = _normalized(quote)
    haystack, _ = _normalized(source_text)
    return len(needle) >= 8 and needle in haystack


def check_version_evidence(
    application_id: int, version: DraftVersionDetail, resume_text: str, job_text: str,
    annotations: list[AnnotationDetail] | None = None,
) -> EvidenceReport:
    lines: list[EvidenceLine] = []
    counts = {"resume": 0, "job": 0, "unmatched": 0, "job_as_resume": 0}
    linked = {(item.document, item.section_index, item.line_index): item
              for item in annotations or []}
    resume_index = _normalized(resume_text)
    job_index = _normalized(job_text)
    for kind, document in (("resume", version.resume), ("letter", version.cover_letter)):
        for section_index, section in enumerate(document.sections):
            for line_index, line in enumerate(section.lines):
                found_resume = _find_excerpt(line, resume_text, resume_index)
                found_job = _find_excerpt(line, job_text, job_index) if found_resume is None else None
                source = "resume" if found_resume else "job" if found_job else None
                excerpt = found_resume or found_job
                counts[source or "unmatched"] += 1
                if kind == "resume" and source == "job":
                    attention = "job_as_resume"
                    reason = "简历行仅在岗位原文中命中，不能据此作为个人经历；请重点核对。"
                    counts["job_as_resume"] += 1
                elif source is None:
                    attention = "review"
                    reason = "未找到整行字面匹配；即使人工关联片段，也仍须核对表述。"
                else:
                    attention = "literal_only"
                    reason = "仅发现字面匹配，不能据此证明事实真实或表述准确。"
                lines.append(EvidenceLine(
                    document=kind, section_index=section_index, line_index=line_index,
                    section=section.heading, line_number=line_index + 1, text=line,
                    source=source, source_excerpt=excerpt[0] if excerpt else None,
                    source_offset=excerpt[1] if excerpt else None,
                    annotation=linked.get((kind, section_index, line_index)),
                    attention=attention, attention_reason=reason,
                ))
    return EvidenceReport(
        application_id=application_id, version=version.version, lines=lines,
        resume_hits=counts["resume"], job_hits=counts["job"], unmatched=counts["unmatched"],
        job_as_resume=counts["job_as_resume"],
    )


def _document_lines(document: DraftDocument) -> list[str]:
    result = [f"标题：{document.title}"]
    for section in document.sections:
        result.append(f"[{section.heading}]")
        result.extend(section.lines)
    return result


def compare_versions(
    application_id: int, previous: DraftVersionDetail, current: DraftVersionDetail,
) -> VersionComparison:
    def diff(before: DraftDocument, after: DraftDocument) -> list[str]:
        return list(unified_diff(
            _document_lines(before), _document_lines(after),
            fromfile=f"版本 {previous.version}", tofile=f"版本 {current.version}",
            lineterm="",
        ))

    return VersionComparison(
        application_id=application_id, from_version=previous.version,
        to_version=current.version,
        resume_diff=diff(previous.resume, current.resume),
        cover_letter_diff=diff(previous.cover_letter, current.cover_letter),
    )
