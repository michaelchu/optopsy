"""PostgreSQL-backed data store for historical market data.

Stores options and stock data in proper relational tables instead of parquet
files, making it easy to inspect and manage data on production deployments
(e.g. Railway).

Tables are created lazily on first use via ``ensure_tables()``.
"""

import logging
import os

import pandas as pd
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Index,
    MetaData,
    Table,
    Text,
    create_engine,
    delete,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

from optopsy.data.providers.store import DataStore

_log = logging.getLogger(__name__)

metadata = MetaData()

# ---------------------------------------------------------------------------
# Table definitions
# ---------------------------------------------------------------------------

options_data = Table(
    "options_data",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("underlying_symbol", Text, nullable=False),
    Column("option_type", Text, nullable=False),
    Column("expiration", DateTime, nullable=False),
    Column("quote_date", DateTime, nullable=False),
    Column("strike", Float, nullable=False),
    Column("bid", Float),
    Column("ask", Float),
    Column("volume", Float),
    Column("delta", Float),
    Column("gamma", Float),
    Column("theta", Float),
    Column("vega", Float),
    Column("rho", Float),
    Column("implied_volatility", Float),
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("last", Float),
    Column("open_interest", Float),
    Column("midpoint", Float),
    Column("moneyness", Float),
    Column("theoretical", Float),
    Column("dte", Float),
    Column("expiration_type", Text),
)

Index(
    "ix_options_data_dedup",
    options_data.c.underlying_symbol,
    options_data.c.quote_date,
    options_data.c.expiration,
    options_data.c.strike,
    options_data.c.option_type,
    options_data.c.expiration_type,
    unique=True,
)

Index(
    "ix_options_data_symbol",
    options_data.c.underlying_symbol,
)

Index(
    "ix_options_data_symbol_quote_date",
    options_data.c.underlying_symbol,
    options_data.c.quote_date,
)

stocks_data = Table(
    "stocks_data",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("underlying_symbol", Text, nullable=False),
    Column("date", DateTime, nullable=False),
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float),
    Column("volume", Float),
)

Index(
    "ix_stocks_data_dedup",
    stocks_data.c.underlying_symbol,
    stocks_data.c.date,
    unique=True,
)

Index(
    "ix_stocks_data_symbol",
    stocks_data.c.underlying_symbol,
)

# Maps category names to table objects
_CATEGORY_TABLE = {
    "options": options_data,
    "yf_stocks": stocks_data,
}


def ensure_tables(engine) -> None:
    """Create tables and indexes if they don't already exist."""
    metadata.create_all(engine)
    _log.debug("Data store tables ensured")


def _normalize_db_url(url: str) -> str:
    """Normalize a database URL for SQLAlchemy sync usage."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    # Strip async driver prefixes
    for async_prefix, sync_prefix in [
        ("postgresql+asyncpg://", "postgresql://"),
        ("postgresql+aiopg://", "postgresql://"),
    ]:
        if url.startswith(async_prefix):
            url = sync_prefix + url[len(async_prefix) :]
    return url


class PostgresStore(DataStore):
    """PostgreSQL-backed data store for historical market data."""

    def __init__(self, db_url: str | None = None):
        url = db_url or os.environ.get("DATABASE_URL", "")
        self._url = _normalize_db_url(url)
        self._engine = create_engine(self._url)
        ensure_tables(self._engine)

    def _table(self, category: str) -> Table:
        tbl = _CATEGORY_TABLE.get(category)
        if tbl is None:
            raise ValueError(
                f"Unknown category {category!r}. Supported: {list(_CATEGORY_TABLE)}"
            )
        return tbl

    def _data_columns(self, table: Table) -> list[str]:
        """Return column names excluding the auto-increment ``id``."""
        return [c.name for c in table.columns if c.name != "id"]

    def read(self, category: str, symbol: str) -> pd.DataFrame | None:
        tbl = self._table(category)
        stmt = select(*[tbl.c[c] for c in self._data_columns(tbl)]).where(
            tbl.c.underlying_symbol == symbol.upper()
        )
        with self._engine.connect() as conn:
            df = pd.read_sql(stmt, conn)
        if df.empty:
            return None
        _log.debug("PG read: %s/%s (%d rows)", category, symbol, len(df))
        return df

    def write(self, category: str, symbol: str, df: pd.DataFrame) -> None:
        tbl = self._table(category)
        data_cols = self._data_columns(tbl)
        # Only keep columns that exist in both the DataFrame and the table
        cols_to_write = [c for c in data_cols if c in df.columns]
        write_df = df[cols_to_write].copy()

        with self._engine.begin() as conn:
            conn.execute(delete(tbl).where(tbl.c.underlying_symbol == symbol.upper()))
            if not write_df.empty:
                write_df.to_sql(
                    tbl.name,
                    conn,
                    if_exists="append",
                    index=False,
                    method="multi",
                    chunksize=10_000,
                )
        _log.debug("PG write: %s/%s (%d rows)", category, symbol, len(write_df))

    def merge_and_save(
        self,
        category: str,
        symbol: str,
        new_df: pd.DataFrame,
        dedup_cols: list[str] | None = None,
    ) -> pd.DataFrame:
        tbl = self._table(category)
        data_cols = self._data_columns(tbl)
        cols_to_write = [c for c in data_cols if c in new_df.columns]
        write_df = new_df[cols_to_write].copy()

        if write_df.empty:
            existing = self.read(category, symbol)
            return existing if existing is not None else pd.DataFrame()

        # Find the unique constraint columns that are present in the data
        if dedup_cols:
            conflict_cols = [c for c in dedup_cols if c in cols_to_write]
        else:
            conflict_cols = []

        if conflict_cols:
            # Use PostgreSQL upsert: INSERT ... ON CONFLICT DO UPDATE
            update_cols = [c for c in cols_to_write if c not in conflict_cols]
            rows = write_df.to_dict(orient="records")
            with self._engine.begin() as conn:
                for i in range(0, len(rows), 10_000):
                    chunk = rows[i : i + 10_000]
                    stmt = pg_insert(tbl).values(chunk)
                    if update_cols:
                        stmt = stmt.on_conflict_do_update(
                            index_elements=conflict_cols,
                            set_={c: stmt.excluded[c] for c in update_cols},
                        )
                    else:
                        stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
                    conn.execute(stmt)
        else:
            # No dedup columns — just append
            with self._engine.begin() as conn:
                write_df.to_sql(
                    tbl.name,
                    conn,
                    if_exists="append",
                    index=False,
                    method="multi",
                    chunksize=10_000,
                )

        _log.debug("PG merge: %s/%s (%d new rows)", category, symbol, len(write_df))
        # Return the full dataset for this symbol
        result = self.read(category, symbol)
        return result if result is not None else write_df

    def clear(self, symbol: str | None = None, category: str | None = None) -> int:
        total = 0
        if category:
            tables = {category: _CATEGORY_TABLE[category]}
        else:
            tables = _CATEGORY_TABLE
        for tbl in tables.values():
            with self._engine.begin() as conn:
                if symbol:
                    stmt = delete(tbl).where(tbl.c.underlying_symbol == symbol.upper())
                else:
                    stmt = delete(tbl)
                result = conn.execute(stmt)
                total += result.rowcount
        return total

    def size(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for category, tbl in _CATEGORY_TABLE.items():
            stmt = select(tbl.c.underlying_symbol, func.count().label("cnt")).group_by(
                tbl.c.underlying_symbol
            )
            with self._engine.connect() as conn:
                for row in conn.execute(stmt):
                    result[f"{category}/{row.underlying_symbol}.db"] = row.cnt
        return result

    def total_size_bytes(self) -> int:
        total = 0
        with self._engine.connect() as conn:
            for tbl in _CATEGORY_TABLE.values():
                row = conn.execute(
                    text("SELECT pg_total_relation_size(:tbl)"),
                    {"tbl": tbl.name},
                ).scalar()
                if row:
                    total += row
        return total
