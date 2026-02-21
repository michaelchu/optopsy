import logging
import os
from datetime import date, timedelta

import pandas as pd

_log = logging.getLogger(__name__)

_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".optopsy", "cache")

# Gaps smaller than this many calendar days are treated as market holidays /
# weekends and are NOT re-fetched.  Gaps larger than this indicate missing data.
_INTERIOR_GAP_THRESHOLD = 5


def compute_date_gaps(
    cached_df: pd.DataFrame | None,
    start_dt: date | None,
    end_dt: date | None,
    date_column: str = "quote_date",
) -> list[tuple[str | None, str | None]]:
    """Compute date ranges missing from *cached_df* that need to be fetched.

    Checks three kinds of gaps:

    1. **Before** — requested start is earlier than the cached min.
    2. **After** — requested end is later than the cached max (or open-ended).
    3. **Interior** — consecutive cached dates within the requested range are
       more than ``_INTERIOR_GAP_THRESHOLD`` calendar days apart, suggesting
       missing data (e.g. a partial fetch failure).

    Returns ``[(None, None)]`` to mean "fetch everything" (no cache), or a
    list of ``(start_str, end_str)`` tuples for each missing range.
    """
    if cached_df is None or cached_df.empty or date_column not in cached_df.columns:
        return [(str(start_dt) if start_dt else None, str(end_dt) if end_dt else None)]

    cached_dates = pd.to_datetime(cached_df[date_column]).dt.date
    cached_min = cached_dates.min()
    cached_max = cached_dates.max()

    gaps: list[tuple[str | None, str | None]] = []

    # Gap before cached range
    if start_dt and start_dt < cached_min:
        gaps.append((str(start_dt), str(cached_min - timedelta(days=1))))

    # Interior gaps — check consecutive cached dates for holes that overlap
    # with the requested range.  A gap between (prev, curr) is relevant when
    # it *intersects* [overlap_start, overlap_end].
    overlap_start = max(start_dt, cached_min) if start_dt else cached_min
    overlap_end = min(end_dt, cached_max) if end_dt else cached_max
    if overlap_start <= overlap_end:
        unique_dates = sorted(cached_dates.unique())
        for prev, curr in zip(unique_dates, unique_dates[1:]):
            day_gap = (curr - prev).days
            if day_gap <= _INTERIOR_GAP_THRESHOLD:
                continue
            hole_start = prev + timedelta(days=1)
            hole_end = curr - timedelta(days=1)
            clamped_start = max(hole_start, overlap_start)
            clamped_end = min(hole_end, overlap_end)
            if clamped_start <= clamped_end:
                gaps.append((str(clamped_start), str(clamped_end)))

    # Gap after cached range.
    # Only fetch beyond cached_max when the user explicitly requested an end
    # date past what we have, OR when a specific start_date was given that
    # implies they want data up to today (open-ended but intentional).
    # A fully open-ended request (no start_dt, no end_dt) means "use the
    # cache as-is" — don't trigger a live fetch just because today > cached_max.
    if end_dt and end_dt > cached_max:
        gaps.append((str(cached_max + timedelta(days=1)), str(end_dt)))
    elif end_dt is None and start_dt is not None:
        # start_dt given but no end_dt → user wants data from start_dt onward;
        # fetch the tail if cached_max doesn't already cover start_dt onward.
        gap_start_date = max(cached_max + timedelta(days=1), start_dt)
        gaps.append((str(gap_start_date), None))

    return gaps


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
