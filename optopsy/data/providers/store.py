"""Abstract base class for data store backends.

Defines the interface that both ``ParquetCache`` (file-based) and
``PostgresStore`` (database-backed) implement, allowing transparent
backend selection via ``get_store()``.
"""

from abc import ABC, abstractmethod

import pandas as pd


class DataStore(ABC):
    """Abstract interface for data store backends."""

    @abstractmethod
    def read(self, category: str, symbol: str) -> pd.DataFrame | None:
        """Load stored data for *(category, symbol)*, or ``None`` if absent."""

    @abstractmethod
    def write(self, category: str, symbol: str, df: pd.DataFrame) -> None:
        """Persist *df* for *(category, symbol)*, replacing any existing data."""

    @abstractmethod
    def merge_and_save(
        self,
        category: str,
        symbol: str,
        new_df: pd.DataFrame,
        dedup_cols: list[str] | None = None,
    ) -> pd.DataFrame:
        """Merge *new_df* with existing data, deduplicate, and persist."""

    @abstractmethod
    def clear(self, symbol: str | None = None) -> int:
        """Remove stored data.  Returns count of items deleted."""

    @abstractmethod
    def size(self) -> dict[str, int]:
        """Return per-entry size information (bytes for files, rows for DB)."""

    @abstractmethod
    def total_size_bytes(self) -> int:
        """Return total storage size in bytes."""
