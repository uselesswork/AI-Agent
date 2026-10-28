"""向配置数据库添加六条虚构记录；重复执行跳过已有标记，不覆盖记录。"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, func, insert, inspect, select
from sqlalchemy.engine import Engine

from app.core.config import get_settings
from app.models.application import ApplicationCreate, ApplicationDetail
from app.services.application_repository import applications_table, metadata
from app.services.application_relations import add_event, attach_snapshot
from app.core.database_schema import users
from app.core.user_scope import bind_user, reset_user

MARKER = "board-demo-v1"
DIMENSIONS = [("技能匹配", 35), ("项目经验", 25), ("教育背景", 15),
              ("实习经历", 15), ("基本条件", 10)]
SCENARIOS = [
    ("星河实验室", "Python 后端实习生", "上海", "待投递", 86, "openai"),
    ("青禾数据", "数据工程实习生", "杭州", "已投递", 72, "deepseek"),
    ("云杉软件", "测试开发实习生", "北京", "笔试", 78, "openai"),
    ("明川智能", "AI 应用开发实习生", "深圳", "面试", 90, "deepseek"),
    ("海棠科技", "平台开发实习生", "成都", "Offer", 94, "openai"),
    ("远山系统", "Java 后端实习生", "广州", "已拒绝", 48, "deepseek"),
]


def build_samples() -> list[ApplicationCreate]:
    """全部为手工夹具，分数仅用于界面测试，不代表模型评估。"""
    samples = []
    quote = "使用 Python、FastAPI 和 MySQL 开发课程管理系统，编写 pytest 接口测试。"
    for number, (company, title, city, status, score, provider) in enumerate(SCENARIOS, 1):
        required = "Java" if score < 60 else "Python"
        samples.append(ApplicationCreate.model_validate({
            "resume_filename": f"{MARKER}-{number:02d}.txt",
            "candidate_profile": {
                "basic_info": {"name": "测试候选人小林", "email": "demo@example.com"},
                "job_targets": ["后端开发实习生"],
                "summary": "虚构在校生，仅用于求职看板功能测试。",
                "education": [{"institution": "示例大学（虚构）", "degree": "本科",
                               "major": "软件工程"}],
                "skills": [{"name": "Python", "category": "编程语言",
                            "evidence": [{"quote": quote, "source_section": "测试项目"}]}],
                "projects": [{"name": "课程管理系统（虚构）", "description": quote,
                              "technologies": ["Python", "FastAPI", "MySQL", "pytest"],
                              "evidence": [{"quote": quote}]}],
                "warnings": ["人工构造测试画像，不来自真实简历。"],
            },
            "job_profile": {
                "title": f"【测试】{title}", "company": f"{company}（虚构）",
                "location": city, "education": "本科在读", "internship_duration": "至少三个月",
                "responsibilities": ["参与业务接口开发和自动化测试"],
                "required_skills": [required, "SQL"], "preferred_skills": ["Docker"],
                "requirements": [{"name": required, "category": "技能", "importance": "必须",
                                  "evidence": f"熟悉 {required} 编程。"}],
                "warnings": ["虚构招聘信息，岗位链接仅为占位。"],
            },
            "match_result": {
                "overall_score": score,
                "recommendation": "建议投递" if score >= 80 else (
                    "谨慎投递" if score >= 60 else "暂不建议投递"),
                "summary": f"人工测试报告：{score} 分，用于验证筛选排序，不作求职判断。",
                "dimensions": [{"name": name, "weight": weight, "score": score,
                                "reason": "人工设定测试值；非模型评分。"}
                               for name, weight in DIMENSIONS],
                "assessments": [{"requirement": required,
                                 "status": "无法确认" if required == "Java" else "满足",
                                 "reason": "测试画像只提供 Python 项目证据。",
                                 "resume_evidence": [quote] if required == "Python" else [],
                                 "job_evidence": f"熟悉 {required} 编程。"}],
                "strengths": ["示例项目包含接口开发与测试"],
                "gaps": ["实习周期和到岗时间尚未确认"],
                "resume_suggestions": ["补充真实的项目职责与可验证成果"],
                "warnings": ["全量数据为虚构测试夹具，没有调用任何大模型。"],
            },
            "provider": provider, "model": "manual-test-fixture",
            "status": status, "job_url": f"https://example.com/jobs/{MARKER}-{number:02d}",
            "notes": f"[{MARKER}] 虚构测试记录，可用于修改状态、备注或删除。",
        }))
    return samples


def seed(engine: Engine) -> tuple[int, int]:
    samples = build_samples()
    names = [sample.resume_filename for sample in samples]
    metadata.create_all(engine)
    inserted = 0
    with engine.begin() as connection:
        existing = set(connection.execute(select(applications_table.c.resume_filename).where(
            applications_table.c.resume_filename.in_(names)
        )).scalars())
        for number, sample in enumerate(samples):
            if sample.resume_filename in existing:
                continue
            values = sample.model_dump(mode="json")
            now = datetime.now(UTC)
            values.update(created_at=now - timedelta(days=number + 1),
                          updated_at=now - timedelta(hours=number))
            values.update(attach_snapshot(connection, values, sample.resume_filename))
            result = connection.execute(insert(applications_table).values(**values))
            add_event(connection, result.inserted_primary_key[0], "created", None,
                      sample.status, now, "虚构测试记录初始化；不代表真实投递历史")
            inserted += 1
    return inserted, len(samples) - inserted


def verify(engine: Engine) -> list[tuple]:
    names = [sample.resume_filename for sample in build_samples()]
    with engine.connect() as connection:
        rows = connection.execute(select(applications_table).where(
            applications_table.c.resume_filename.in_(names)
        ).order_by(applications_table.c.id)).mappings().all()
    result = []
    for row in rows:
        job, report = row["job_profile"], row["match_result"]
        legacy = {key: row[key] for key in (
            "id", "resume_filename", "candidate_profile", "job_profile", "match_result",
            "provider", "model", "status", "job_url", "notes", "created_at", "updated_at",
        )}
        detail = ApplicationDetail.model_validate({
            **legacy, "company": job.get("company"), "title": job.get("title"),
            "location": job.get("location"), "overall_score": report["overall_score"],
            "recommendation": report["recommendation"],
        })
        result.append((detail.id, detail.title, detail.status, detail.overall_score))
    return result


def main() -> int:
    engine = None
    try:
        url = get_settings().validated_database_url()
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
        if "users" in inspect(engine).get_table_names():
            with engine.connect() as connection:
                if connection.scalar(select(func.count()).select_from(users)):
                    raise ValueError("已启用账号；旧测试数据脚本不再允许向共享库写入。")
        token = bind_user(1)
        try:
            inserted, skipped = seed(engine)
        finally:
            reset_user(token)
        print(f"新增 {inserted} 条，跳过已有 {skipped} 条。")
        rows = verify(engine)
        print(f"数据库回读及完整结构校验通过：{len(rows)} 条测试记录。")
        for record_id, title, status, score in rows:
            print(f"ID={record_id} | {title} | {status} | {score} 分")
        return 0
    except Exception as exc:
        # 异常文本可能携带连接地址，禁止直接打印。
        original = getattr(exc, "orig", None)
        args = getattr(original, "args", ())
        code = args[0] if args and isinstance(args[0], int) else "无"
        print(f"操作失败，类型={type(exc).__name__}，数据库错误码={code}。")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
