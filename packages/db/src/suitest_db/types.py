"""Portable column types across dialects (PostgreSQL + SQLite)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, cast

from sqlalchemy import CHAR, JSON, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import TypeDecorator

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect
    from sqlalchemy.sql.type_api import TypeEngine

# JSONB on PostgreSQL, text-based JSON on SQLite/other dialects.
PortableJSON = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class UserGUID(TypeDecorator[uuid.UUID]):
    """UUID storage compatible with FastAPI-Users on PostgreSQL and SQLite."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[object]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(cast("TypeEngine[object]", UUID(as_uuid=True)))
        return dialect.type_descriptor(cast("TypeEngine[object]", CHAR(36)))

    def process_bind_param(
        self, value: uuid.UUID | str | None, dialect: Dialect
    ) -> uuid.UUID | str | None:
        if value is None:
            return None
        parsed = value if isinstance(value, uuid.UUID) else uuid.UUID(value)
        return parsed if dialect.name == "postgresql" else str(parsed)

    def process_result_value(
        self, value: uuid.UUID | str | None, _dialect: Dialect
    ) -> uuid.UUID | None:
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
