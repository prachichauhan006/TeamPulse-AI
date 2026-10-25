import json
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.constants import EMBEDDING_DIMENSIONS


class Vector1536(TypeDecorator):
    """PostgreSQL pgvector column with a JSON representation for SQLite tests."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(EMBEDDING_DIMENSIONS))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect) -> Any:
        if value is None or dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect) -> Any:
        if value is None or dialect.name == "postgresql":
            return value
        return json.loads(value)
