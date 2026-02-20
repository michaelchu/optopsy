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
        safe_category = os.path.basename(category)
        safe_symbol = os.path.basename(symbol)
        return os.path.join(
            self._cache_dir, safe_category, f"{safe_symbol.upper()}.parquet"
        )

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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            df.to_parquet(path, index=False, engine="pyarrow")
            _log.debug("Cache written: %s (%d rows)", path, len(df))
        except Exception as exc:
            _log.warning("Failed to write cache %s: %s", path, exc)

    def merge_and_save(
        self,
        category: str,
        symbol: str,
        new_df: pd.DataFrame,
        dedup_cols: list[str] | None = None,
    ) -> pd.DataFrame:
        """Merge *new_df* with any existing cache and deduplicate.

        *dedup_cols* — columns that form a natural key for dedup.  When
        provided, only the **last** occurrence of each key is kept so that
        newer data wins.  Falls back to full-row dedup when ``None``.
        """
        existing = self.read(category, symbol)
        if existing is not None and not existing.empty:
            merged = pd.concat([existing, new_df], ignore_index=True)
        else:
            merged = new_df.copy()

        if dedup_cols:
            present = [c for c in dedup_cols if c in merged.columns]
            if present:
                merged = merged.drop_duplicates(subset=present, keep="last")
            else:
                merged = merged.drop_duplicates()
        else:
            merged = merged.drop_duplicates()

        self.write(category, symbol, merged)
        return merged

    def clear(self, symbol: str | None = None) -> int:
        """Remove cached files.

        If *symbol* is given, remove that symbol across all categories.
        If ``None``, remove everything.  Returns number of files deleted.
        """
        count = 0
        if not os.path.exists(self._cache_dir):
            return count
        for category in os.listdir(self._cache_dir):
            cat_path = os.path.join(self._cache_dir, category)
            if not os.path.isdir(cat_path):
                continue
            if symbol:
                target = os.path.join(cat_path, f"{symbol.upper()}.parquet")
                if os.path.exists(target):
                    os.remove(target)
                    count += 1
            else:
                for fname in os.listdir(cat_path):
                    if fname.endswith(".parquet"):
                        os.remove(os.path.join(cat_path, fname))
                        count += 1
        return count

    def size(self) -> dict[str, int]:
        """Return ``{category/SYMBOL.parquet: bytes}`` for all cached files."""
        result: dict[str, int] = {}
        if not os.path.exists(self._cache_dir):
            return result
        for category in sorted(os.listdir(self._cache_dir)):
            cat_path = os.path.join(self._cache_dir, category)
            if not os.path.isdir(cat_path):
                continue
            for fname in sorted(os.listdir(cat_path)):
                if fname.endswith(".parquet"):
                    fpath = os.path.join(cat_path, fname)
                    result[f"{category}/{fname}"] = os.path.getsize(fpath)
        return result

    def total_size_bytes(self) -> int:
        """Return total cache size in bytes."""
        return sum(self.size().values())
