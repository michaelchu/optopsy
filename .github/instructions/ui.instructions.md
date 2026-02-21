---
applyTo: "optopsy/ui/**/*.py"
---

# UI Module Review Instructions

## Module Structure

- `agent.py` — `OptopsyAgent` class with tool-calling loop over LiteLLM, streaming, and message compaction.
- `tools/` — Tool registry: schemas in `_schemas.py`, shared helpers in `_helpers.py`, execution in `_executor.py`.
- `providers/` — Pluggable data provider system. Each provider subclasses `DataProvider` from `base.py` and is auto-detected via its `env_key` environment variable.
- `providers/cache.py` — `ParquetCache` at `~/.optopsy/cache/`. No TTL — historical data is immutable.

## Security

- API keys must come from environment variables, never hardcoded or logged.
- User-supplied file paths in tool handlers must be validated against path traversal.
- All LLM tool arguments must be validated and sanitized before execution.
- Do not trust or echo raw LLM output into shell commands or file paths.

## Provider Conventions

- New providers subclass `DataProvider` and implement `name`, `env_key`, `get_tool_schemas()`, `get_tool_names()`, `execute()`.
- Register new providers in `providers/__init__.py`.
- Cache writes use `ParquetCache.merge_and_save()` for incremental updates.
