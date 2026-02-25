"""Centralised data-directory paths for the Optopsy Chat UI.

Every on-disk location (cache, results, storage, database, auth secret)
is derived from a single root that defaults to ``~/.optopsy`` but can be
overridden by setting the ``OPTOPSY_DATA_DIR`` environment variable.

This makes it straightforward to point all persistent data at a mounted
volume in production (e.g. Railway, Render, Fly.io).
"""

import os
from pathlib import Path


def _resolve_data_dir() -> Path:
    """Return the base data directory, respecting ``OPTOPSY_DATA_DIR``."""
    env = os.environ.get("OPTOPSY_DATA_DIR")
    if env:
        return Path(env).expanduser()
    return Path("~/.optopsy").expanduser()


DATA_DIR: Path = _resolve_data_dir()

CACHE_DIR: Path = DATA_DIR / "cache"
RESULTS_DIR: Path = DATA_DIR / "results"
STORAGE_DIR: Path = DATA_DIR / "storage"
DB_PATH: Path = DATA_DIR / "chat.db"
AUTH_SECRET_PATH: Path = DATA_DIR / "auth_secret"
