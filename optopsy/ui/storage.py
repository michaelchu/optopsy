"""Local filesystem storage client for Chainlit element persistence.

Stores element content (e.g. Plotly chart JSON) on disk so that charts
survive session resume.  Files are served back via a FastAPI route
registered in ``app.py``.
"""

from pathlib import Path
from typing import Any, Dict, Union

import aiofiles
from chainlit.data.storage_clients.base import BaseStorageClient

from optopsy.ui.paths import STORAGE_DIR

STORAGE_ROUTE_PREFIX = "/optopsy-storage"


class LocalStorageClient(BaseStorageClient):
    """Persist element blobs to the local filesystem."""

    def __init__(self, storage_dir: Path = STORAGE_DIR):
        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, object_key: str) -> Path:
        """Resolve *object_key* under the storage dir, rejecting traversal."""
        resolved = (self._storage_dir / object_key).resolve()
        if not resolved.is_relative_to(self._storage_dir.resolve()):
            raise ValueError("Invalid object_key — path traversal detected")
        return resolved

    async def upload_file(
        self,
        object_key: str,
        data: Union[bytes, str],
        mime: str = "application/octet-stream",
        overwrite: bool = True,
        content_disposition: str | None = None,
    ) -> Dict[str, Any]:
        file_path = self._safe_path(object_key)
        if not overwrite and file_path.exists():
            raise FileExistsError(f"File already exists: {object_key}")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(data)
        else:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(data)
        return {
            "object_key": object_key,
            "url": f"{STORAGE_ROUTE_PREFIX}/{object_key}",
        }

    async def delete_file(self, object_key: str) -> bool:
        file_path = self._safe_path(object_key)
        if file_path.is_file():
            file_path.unlink()
            return True
        return False

    async def get_read_url(self, object_key: str) -> str:
        self._safe_path(object_key)
        return f"{STORAGE_ROUTE_PREFIX}/{object_key}"

    async def close(self) -> None:
        pass
