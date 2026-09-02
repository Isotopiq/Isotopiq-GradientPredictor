"""Cross-dialect JSON type: JSONB on Postgres, JSON on SQLite (for tests)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator


class JSONBCompat(TypeDecorator):
    """Use JSONB on Postgres, JSON elsewhere (for SQLite test compat)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect):  # type: ignore[override]
        return value

    def process_result_value(self, value: Any, dialect):  # type: ignore[override]
        return value
