"""UI-layer EODHD provider that adds Pydantic argument model support.

Inherits all download/fetch logic from ``optopsy.data.providers.eodhd``
and adds ``get_arg_model()`` which requires the UI tools layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from optopsy.data.providers.eodhd import EODHDProvider as _BaseEODHDProvider

if TYPE_CHECKING:
    from pydantic import BaseModel


class EODHDProvider(_BaseEODHDProvider):
    """EODHD provider with UI-layer argument validation."""

    def get_arg_model(self, tool_name: str) -> type[BaseModel] | None:
        if tool_name == "fetch_options_data":
            from ..tools._models import FetchOptionsDataArgs

            return FetchOptionsDataArgs
        if tool_name == "download_options_data":
            from ..tools._models import DownloadOptionsDataArgs

            return DownloadOptionsDataArgs
        return None
