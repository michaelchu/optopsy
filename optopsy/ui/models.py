"""SQLAlchemy table definitions for the Chainlit persistence layer.

Defines a single schema that emits dialect-appropriate DDL for both SQLite
and PostgreSQL via ``metadata.create_all(engine)``.

On PostgreSQL, columns use native ``UUID``, ``JSONB``, ``TEXT[]``, and
``BOOLEAN`` types.  On SQLite the same definitions fall back to ``TEXT``
and ``INTEGER`` — no hand-written SQL required.
"""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

metadata = MetaData()

# ---------------------------------------------------------------------------
# Dialect-aware column types
#
# On PostgreSQL these resolve to native UUID / JSONB / TEXT[].
# On SQLite they fall back to plain TEXT so Chainlit's raw-SQL data layer
# (which serialises everything to strings) keeps working unchanged.
# ---------------------------------------------------------------------------
_UUID = Text().with_variant(PG_UUID(as_uuid=False), "postgresql")
_JSON = Text().with_variant(JSONB(), "postgresql")
_TAGS = Text().with_variant(PG_ARRAY(Text), "postgresql")

users = Table(
    "users",
    metadata,
    Column("id", _UUID, primary_key=True),
    Column("identifier", Text, nullable=False, unique=True),
    Column("metadata", _JSON, nullable=False),
    Column("createdAt", Text),
)

threads = Table(
    "threads",
    metadata,
    Column("id", _UUID, primary_key=True),
    Column("createdAt", Text),
    Column("name", Text),
    Column("userId", _UUID, ForeignKey("users.id", ondelete="CASCADE")),
    Column("userIdentifier", Text),
    Column("tags", _TAGS),
    Column("metadata", _JSON),
)

steps = Table(
    "steps",
    metadata,
    Column("id", _UUID, primary_key=True),
    Column("name", Text, nullable=False),
    Column("type", Text, nullable=False),
    Column(
        "threadId",
        _UUID,
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("parentId", _UUID),
    Column("streaming", Boolean, nullable=False),
    Column("waitForAnswer", Boolean),
    Column("isError", Boolean),
    Column("metadata", _JSON),
    Column("tags", _TAGS),
    Column("input", Text),
    Column("output", Text),
    Column("createdAt", Text),
    Column("command", Text),
    Column("start", Text),
    Column("end", Text),
    Column("generation", _JSON),
    Column("showInput", Text),
    Column("language", Text),
    Column("indent", Integer),
    Column("defaultOpen", Boolean),
)

elements = Table(
    "elements",
    metadata,
    Column("id", _UUID, primary_key=True),
    Column("threadId", _UUID, ForeignKey("threads.id", ondelete="CASCADE")),
    Column("type", Text),
    Column("url", Text),
    Column("chainlitKey", Text),
    Column("name", Text, nullable=False),
    Column("display", Text),
    Column("objectKey", Text),
    Column("size", Text),
    Column("page", Integer),
    Column("language", Text),
    Column("forId", _UUID),
    Column("mime", Text),
    Column("props", _JSON),
)

feedbacks = Table(
    "feedbacks",
    metadata,
    Column("id", _UUID, primary_key=True),
    Column("forId", _UUID, nullable=False),
    Column("threadId", _UUID, ForeignKey("threads.id", ondelete="CASCADE")),
    Column("value", Integer, nullable=False),
    Column("comment", Text),
)
