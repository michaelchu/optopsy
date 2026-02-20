import logging
import os

import pandas as pd

_log = logging.getLogger(__name__)

_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".optopsy", "cache")


class ParquetCache:
    """Simple parquet-based cache for immutable historical data.

    Each (category, symbol) pair maps to a single parquet file at:
        ~/.optopsy/cache/{category}/{SYMBOL}.parquet

    No TTL, no eviction — historical data is immutable.
    """

    def __init__(self, cache_dir: str = _CACHE_DIR):
        self._cache_dir = cache_dir

    def _path(self, category: str, symbol: str) -> str:
        directory = os.path.join(self._cache_dir, category)
        os.makedirs(directory, exist_ok=True)
        return os.path.join(directory, f"{symbol.upper()}.parquet")

    def read(self, category: str, symbol: str) -> pd.DataFrame | None:
        path = self._path(category, symbol)
        if not os.path.exists(path):
            return None
        try:
            df = pd.read_parquet(path)
            _log.debug("Cache hit: %s (%d rows)", path, len(df))
            return df
        except Exception as exc:
            _log.warning("Failed to read cache %s: %s", path, exc)
            return None

    def write(self, category: str, symbol: str, df: pd.DataFrame) -> None:
        path = self._path(category, symbol)
        try:
            df.to_parquet(path, index=False, engine="pyarrow")
            _log.debug("Cache written: %s (%d rows)", path, len(df))
        except Exception as exc:
            _log.warning("Failed to write cache %s: %s", path, exc)

    def merge_and_save(
        self, category: str, symbol: str, new_df: pd.DataFrame
    ) -> pd.DataFrame:
        existing = self.read(category, symbol)
        if existing is not None and not existing.empty:
            merged = pd.concat([existing, new_df], ignore_index=True)
        else:
            merged = new_df.copy()

        merged = merged.drop_duplicates()
        self.write(category, symbol, merged)
        return merged
