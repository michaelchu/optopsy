"""Global parquet cache for result DataFrames (strategies + simulations).

Keys are SHA-256 content hashes of (name, params, dataset_fingerprint).
A JSON index maps hashes to human-readable metadata (type, strategy, params,
display_key, and for simulations: summary).

Storage layout::

    ~/.optopsy/results/
      {hash}.parquet          # full result DataFrame
      _index.json             # hash -> metadata mapping
"""

import fcntl
import hashlib
import json
import logging
import os
import tempfile

import pandas as pd

_log = logging.getLogger(__name__)

_RESULTS_DIR = os.path.join(os.path.expanduser("~"), ".optopsy", "results")


class ResultStore:
    """Global parquet cache for result DataFrames (strategies + simulations).

    Keys are SHA-256 hashes of (name, params, dataset_fingerprint).
    A JSON index maps hashes to human-readable metadata.

    Index mutations are protected by a file lock (``_index.lock``) to
    prevent concurrent writes from clobbering each other.
    """

    def __init__(self, results_dir: str | None = None):
        self._dir = results_dir or _RESULTS_DIR

    @staticmethod
    def make_key(name: str, arguments: dict, dataset_fingerprint: str) -> str:
        """Deterministic cache key for any result (strategy or simulation).

        DataFrame values (e.g. signal columns) are fingerprinted via
        ``pd.util.hash_pandas_object`` so that different signals produce
        different cache keys.
        """
        param_keys = sorted(k for k in arguments.keys() if k not in ("strategy_name",))
        serializable = {}
        for k in param_keys:
            v = arguments[k]
            if isinstance(v, pd.DataFrame):
                serializable[k] = str(pd.util.hash_pandas_object(v, index=False).sum())
            else:
                serializable[k] = v
        params_str = json.dumps(serializable, sort_keys=True, default=str)
        raw = f"{name}:{params_str}:{dataset_fingerprint}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _parquet_path(self, key: str) -> str:
        return os.path.join(self._dir, f"{key}.parquet")

    def _index_path(self) -> str:
        return os.path.join(self._dir, "_index.json")

    def _lock_path(self) -> str:
        return os.path.join(self._dir, "_index.lock")

    def _read_index(self) -> dict[str, dict]:
        path = self._index_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_index(self, index: dict[str, dict]) -> None:
        """Atomically write the index via temp file + rename."""
        fd, tmp = tempfile.mkstemp(dir=self._dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(index, f, indent=2, default=str)
            os.replace(tmp, self._index_path())
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _locked_index_update(self, updater):
        """Run *updater(index)* while holding an exclusive file lock.

        This prevents concurrent writes from clobbering each other's
        index entries.  The lock file is ``_index.lock`` alongside the
        index itself.
        """
        os.makedirs(self._dir, exist_ok=True)
        lock_fd = os.open(self._lock_path(), os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            index = self._read_index()
            updater(index)
            self._write_index(index)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    def write(self, key: str, df: pd.DataFrame, metadata: dict) -> None:
        """Persist a result DataFrame and its metadata.

        Writes the parquet file to a temporary name first, updates the
        index under a file lock, then atomically renames the parquet file
        into place.  This prevents orphaned parquet files without index
        entries.
        """
        os.makedirs(self._dir, exist_ok=True)
        fd, tmp_parquet = tempfile.mkstemp(dir=self._dir, suffix=".parquet.tmp")
        os.close(fd)
        try:
            df.to_parquet(tmp_parquet, index=False, engine="pyarrow")
            self._locked_index_update(lambda idx: idx.__setitem__(key, metadata))
            os.replace(tmp_parquet, self._parquet_path(key))
            _log.debug("ResultStore: wrote %s (%d rows)", key, len(df))
        except BaseException:
            try:
                os.unlink(tmp_parquet)
            except OSError:
                pass
            raise

    def read(self, key: str) -> pd.DataFrame | None:
        """Load a result DataFrame by key, or None if not found."""
        path = self._parquet_path(key)
        if not os.path.exists(path):
            return None
        try:
            return pd.read_parquet(path)
        except Exception as exc:
            _log.warning("ResultStore: failed to read %s: %s", key, exc)
            return None

    def has(self, key: str) -> bool:
        """Check if a result exists on disk."""
        return os.path.exists(self._parquet_path(key))

    def get_metadata(self, key: str) -> dict:
        """Return metadata for a key, or empty dict if not found."""
        return self._read_index().get(key, {})

    def list_all(self) -> dict[str, dict]:
        """Return the full index: {hash -> metadata}."""
        return self._read_index()

    def clear(self, key: str | None = None) -> int:
        """Remove cached results. If key is given, remove just that entry.

        Returns number of files deleted.
        """
        if not os.path.exists(self._dir):
            return 0

        if key:
            count = 0
            path = self._parquet_path(key)
            if os.path.exists(path):
                os.remove(path)
                count = 1

            def _remove_key(index):
                index.pop(key, None)

            self._locked_index_update(_remove_key)
            return count

        # Clear everything
        count = 0
        for fname in os.listdir(self._dir):
            fpath = os.path.join(self._dir, fname)
            if os.path.isfile(fpath):
                os.remove(fpath)
                count += 1
        return count

    def total_size_bytes(self) -> int:
        """Return total size of all cached result files in bytes."""
        if not os.path.exists(self._dir):
            return 0
        total = 0
        for fname in os.listdir(self._dir):
            fpath = os.path.join(self._dir, fname)
            if os.path.isfile(fpath):
                total += os.path.getsize(fpath)
        return total
