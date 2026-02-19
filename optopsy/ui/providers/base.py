"""
DataProvider ABC — base interface for all optopsy data providers.

How to add a new provider
=========================

1. Create a new file in this directory, e.g. ``polygon.py``.

2. Subclass ``DataProvider`` and implement every abstract member::

       # optopsy/ui/providers/polygon.py
       from .base import DataProvider

       class PolygonProvider(DataProvider):

           @property
           def name(self) -> str:
               return "Polygon"          # shown in the chat welcome message

           @property
           def env_key(self) -> str:
               return "POLYGON_API_KEY"   # checked by is_available()

           def get_tool_schemas(self) -> list[dict[str, Any]]:
               # Return OpenAI-compatible function-calling tool schemas.
               # Each schema is {"type": "function", "function": {name, description, parameters}}.
               # See eodhd.py for a complete example.
               return [...]

           def get_tool_names(self) -> list[str]:
               # Must match the "name" values in get_tool_schemas().
               return ["fetch_polygon_options"]

           def execute(self, tool_name, arguments):
               # Dispatch on tool_name, call your API, return (summary, DataFrame | None).
               # Return (error_message, None) on failure — don't raise.
               ...

3. Register the provider in ``__init__.py``::

       from .polygon import PolygonProvider

       ALL_PROVIDERS: list[DataProvider] = [
           EODHDProvider(),
           PolygonProvider(),   # <-- add here
       ]

4. Add the env var to ``.env.example``::

       POLYGON_API_KEY=

Done. No changes needed in tools.py, app.py, or agent.py.

Important conventions
---------------------
- Tool names should be globally unique across all providers.
  Prefix with the provider name, e.g. ``fetch_polygon_options``.
- ``execute()`` returns ``(summary_str, DataFrame | None)``.
  Returning a DataFrame replaces the user's active dataset (used for
  backtesting). Return None for display-only tools (e.g. stock prices)
  — the caller in tools.py uses ``"stock" in tool_name`` to decide
  whether the DataFrame replaces the active dataset or is just displayed.
- ``is_available()`` has a default implementation that checks
  ``os.environ.get(self.env_key)``. Override it if your provider needs
  more complex availability logic (e.g. multiple keys).
- Keep API-specific constants (URLs, column maps) as module-level
  privates in your provider file. See eodhd.py for the pattern.
"""

import os
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class DataProvider(ABC):
    """Base interface for optopsy data providers.

    See module docstring for step-by-step instructions on adding a new provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name, e.g. 'EODHD'."""
        ...

    @property
    @abstractmethod
    def env_key(self) -> str:
        """Environment variable name for the API key."""
        ...

    def is_available(self) -> bool:
        """Return True if the required env var is set and non-empty."""
        return bool(os.environ.get(self.env_key))

    @abstractmethod
    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible function-calling tool schema dicts.

        Each dict must follow the format::

            {
                "type": "function",
                "function": {
                    "name": "fetch_<provider>_<resource>",
                    "description": "...",
                    "parameters": {
                        "type": "object",
                        "properties": { ... },
                        "required": [ ... ],
                    },
                },
            }
        """
        ...

    @abstractmethod
    def get_tool_names(self) -> list[str]:
        """Return tool function names this provider handles.

        Must exactly match the ``name`` values in ``get_tool_schemas()``.
        """
        ...

    @abstractmethod
    def execute(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[str, pd.DataFrame | None]:
        """Execute a tool call and return (summary_text, dataframe_or_none).

        - On success: return a human-readable summary and optionally a DataFrame.
        - On failure: return an error message and None (don't raise exceptions).
        """
        ...
