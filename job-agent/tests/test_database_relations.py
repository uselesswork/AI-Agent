from datetime import UTC, datetime

from sqlalchemy import create_engine, event, func, insert, select

from app.core.database_schema import application_events, applications_table, metadata, resumes
from app.models.application import ApplicationUpdate
from app.services.application_repository import ApplicationRepository
from scripts.init_database import backfill, verify_relations
from scripts.seed_applications import build_samples, seed


def test_relations_state_events_and_deletion(tmp_path):
    repo = ApplicationRepository(f"sqlite+pysqlite:///{(tmp_path / 'relations.db').as_posix()}")
    # 对后续池连接启用 SQLite 外键约束，验证级联和引用限制。
    repo.engine.dispose()

    @event.listens_for(repo.engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        first = repo.create(build_samples()[0])
        second = repo.create(build_samples()[1])
        assert verify_relations(repo.engine)["resumes"] == 1
        repo.update(first.id, ApplicationUpdate(status="已投递"))
        repo.update(first.id, ApplicationUpdate(notes="仅修改备注"))
        with repo.engine.connect() as connection:
            row = connection.execute(select(applications_table).where(
                applications_table.c.id == first.id)).mappings().one()
            assert row["applied_at"] is not None
            events = connection.execute(select(application_events).where(
                application_events.c.application_id == first.id)).mappings().all()
            assert [x["event_type"] for x in events] == ["created", "status_changed"]
        repo.delete(first.id)
        assert repo.get(second.id).id == second.id
        with repo.engine.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(resumes)) == 1
            assert connection.scalar(select(func.count()).select_from(application_events).where(
                application_events.c.application_id == first.id)) == 0
    finally:
        repo.engine.dispose()


def test_seed_and_backfill_repeatable(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'backfill.db').as_posix()}")
    try:
        metadata.create_all(engine)
        assert seed(engine) == (6, 0)
        counts = verify_relations(engine)
        assert counts == {"resumes": 1, "jobs": 6, "match_reports": 6,
                          "applications": 6, "application_events": 6,
                          "draft_versions": 0, "application_sources": 0}
        assert backfill(engine) == 0
        assert seed(engine) == (0, 6)
        assert verify_relations(engine) == counts
    finally:
        engine.dispose()


def test_legacy_snapshot_is_preserved(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    try:
        metadata.create_all(engine)
        data = build_samples()[0].model_dump(mode="json")
        data.update(created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        with engine.begin() as connection:
            connection.execute(insert(applications_table).values(**data))
        assert backfill(engine) == 1
        assert backfill(engine) == 0
        with engine.connect() as connection:
            row = connection.execute(select(applications_table)).mappings().one()
            assert row["match_result"] == data["match_result"]
            assert row["notes"] == data["notes"]
            assert row["applied_at"] is None
            event_row = connection.execute(select(application_events)).mappings().one()
            assert event_row["event_type"] == "snapshot"
        assert verify_relations(engine)["applications"] == 1
    finally:
        engine.dispose()
