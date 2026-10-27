"""草稿单行人工标注；来源原文删除时标注随外键或服务逻辑删除。"""

from datetime import UTC, datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Engine

from app.core.database_schema import draft_annotations, draft_versions
from app.models.annotation import AnnotationDetail, AnnotationWrite


class AnnotationRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_for_version(self, version_id: int) -> list[AnnotationDetail]:
        with self.engine.connect() as connection:
            rows = connection.execute(select(draft_annotations).where(
                draft_annotations.c.version_id == version_id,
            ).order_by(draft_annotations.c.id)).mappings().all()
        return [AnnotationDetail.model_validate(row) for row in rows]

    def upsert(self, application_id: int, version_id: int,
               data: AnnotationWrite) -> AnnotationDetail:
        now = datetime.now(UTC)
        locator = (
            draft_annotations.c.version_id == version_id,
            draft_annotations.c.document == data.document,
            draft_annotations.c.section_index == data.section_index,
            draft_annotations.c.line_index == data.line_index,
        )
        with self.engine.begin() as connection:
            # 同一版本的标注请求串行化，避免两次创建同一行时撞唯一约束。
            connection.execute(select(draft_versions.c.id).where(
                draft_versions.c.id == version_id).with_for_update()).first()
            row_id = connection.scalar(select(draft_annotations.c.id).where(*locator))
            values = dict(source_kind=data.source_kind,
                          source_quote=data.source_quote.strip(), note=data.note.strip(),
                          updated_at=now)
            if row_id is None:
                result = connection.execute(insert(draft_annotations).values(
                    application_id=application_id, version_id=version_id,
                    document=data.document, section_index=data.section_index,
                    line_index=data.line_index, created_at=now, **values,
                ))
                row_id = int(result.inserted_primary_key[0])
            else:
                connection.execute(update(draft_annotations).where(
                    draft_annotations.c.id == row_id).values(**values))
        with self.engine.connect() as connection:
            row = connection.execute(select(draft_annotations).where(
                draft_annotations.c.id == row_id)).mappings().one()
        return AnnotationDetail.model_validate(row)

    def delete(self, version_id: int, document: str,
               section_index: int, line_index: int) -> None:
        with self.engine.begin() as connection:
            connection.execute(delete(draft_annotations).where(
                draft_annotations.c.version_id == version_id,
                draft_annotations.c.document == document,
                draft_annotations.c.section_index == section_index,
                draft_annotations.c.line_index == line_index,
            ))
