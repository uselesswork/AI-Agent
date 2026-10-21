from sqlalchemy import create_engine, insert, select

from app.services.application_repository import applications_table, metadata
from scripts.seed_applications import build_samples, seed, verify


def test_seed_preserves_existing_records_and_skips_duplicates(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'seed.db').as_posix()}")
    try:
        metadata.create_all(engine)
        from datetime import UTC, datetime

        original = build_samples()[0].model_dump(mode="json")
        original.update(resume_filename="existing.txt", notes="原有记录",
                        created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        with engine.begin() as connection:
            connection.execute(insert(applications_table).values(**original))
        assert seed(engine) == (6, 0)
        assert seed(engine) == (0, 6)
        rows = verify(engine)
        assert len(rows) == 6
        assert len({row[2] for row in rows}) == 6
        assert len({row[3] for row in rows}) == 6
        with engine.connect() as connection:
            all_rows = connection.execute(select(applications_table)).mappings().all()
        assert len(all_rows) == 7
        assert all_rows[0]["notes"] == "原有记录"
    finally:
        engine.dispose()
