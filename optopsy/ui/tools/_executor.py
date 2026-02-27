"""Tool handler registry, shared utilities, and main dispatcher.

Each tool handler is registered via the ``@_register`` decorator and invoked
by ``execute_tool()``.  Handlers receive the current session state (active
dataset, named datasets, signals, results) and return a ``ToolResult`` that
carries updated state back to the agent loop.

Handler implementations live in focused submodules:

- ``_data_inspector`` — preview_data, describe_data, suggest_strategy_params
- ``_quality_checks`` — check_data_quality + per-date uniqueness helpers
- ``_signals_builder`` — build_signal, preview_signal, list_signals, fetch_stock_data
- ``_strategy_runners`` — run_strategy, scan_strategies
- ``_simulators`` — simulate, get_simulation_trades
- ``_results_manager`` — compare_results, list_results, inspect_cache, clear_cache
- ``_charts`` — create_chart, plot_vol_surface, iv_term_structure
"""

import logging
from collections.abc import Callable
from typing import Any

import pandas as pd

from ..providers import get_provider_for_tool
from ._helpers import (
    ToolResult,
    _df_to_markdown,
)
from ._schemas import STRATEGY_NAMES

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool handler registry
# ---------------------------------------------------------------------------

_TOOL_HANDLERS: dict[str, Callable[..., ToolResult]] = {}

_PLUGINS_LOADED = False


def _ensure_plugins_loaded() -> None:
    """Load plugin tool handlers and arg models (runs once)."""
    global _PLUGINS_LOADED
    if _PLUGINS_LOADED:
        return

    try:
        from optopsy.plugins import get_plugin_tools

        from ._models import TOOL_ARG_MODELS
    except Exception:
        _log.warning("Plugin tool imports failed", exc_info=True)
        _PLUGINS_LOADED = True
        return

    for reg in get_plugin_tools():
        try:
            for name, handler in reg.get("handlers", {}).items():
                if name in _TOOL_HANDLERS:
                    _log.warning("Plugin overrides built-in tool handler: %s", name)
                _TOOL_HANDLERS[name] = handler
            TOOL_ARG_MODELS.update(reg.get("models", {}))
        except Exception:
            _log.warning("Failed to load plugin tool registry", exc_info=True)

    _PLUGINS_LOADED = True


def _register(name: str):
    """Decorator to register a tool handler function."""

    def decorator(fn: Callable[..., ToolResult]):
        _TOOL_HANDLERS[name] = fn
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Shared helpers (used by multiple handler modules)
# ---------------------------------------------------------------------------


def _fmt_pf(value: float) -> str:
    """Format profit_factor for display, handling infinity and NaN."""
    if value != value:  # NaN check
        return "N/A"
    if value == float("inf"):
        return "\u221e (no losses)"
    return f"{value:.2f}"


# Minimum distinct strikes per quote_date needed for multi-leg strategies.
_STRIKE_THRESHOLDS: dict[str, int] = {
    name: (3 if "butterfly" in name else 4 if "condor" in name else 2)
    for name in STRATEGY_NAMES
    if "butterfly" in name
    or "condor" in name
    or "spread" in name
    or "straddle" in name
    or "strangle" in name
}


def _check_per_date_uniqueness(
    df: pd.DataFrame,
    column: str,
    threshold: int,
    section_title: str,
    unit_label: str,
    strategy_name: str,
    findings: list[str],
    display_parts: list[str],
) -> None:
    """Check that each quote_date has at least *threshold* unique values in *column*."""
    per_date = df.groupby("quote_date")[column].nunique()
    below = per_date[per_date < threshold]
    if not below.empty:
        n_below = len(below)
        total = len(per_date)
        sample = [
            str(d.date()) if hasattr(d, "date") else str(d) for d in below.index[:5]
        ]
        findings.append(
            f"WARN: {n_below}/{total} dates have < {threshold} "
            f"{unit_label} (needed for {strategy_name})"
        )
        display_parts.append(
            f"**{section_title}** — {n_below}/{total} dates "
            f"have fewer than {threshold} {unit_label}\n"
            f"Sample dates: {', '.join(sample)}\n"
        )
    else:
        findings.append(
            f"PASS: all dates have \u2265 {threshold} {unit_label} for {strategy_name}"
        )
        display_parts.append(
            f"**{section_title}** — all dates have \u2265 {threshold} {unit_label}\n"
        )


def _resolve_dataset(
    name: str | None,
    active: pd.DataFrame | None,
    dss: dict[str, pd.DataFrame],
) -> pd.DataFrame | None:
    """Return the dataset for *name*, falling back to *active*."""
    if name:
        return dss.get(name)
    return active


def _require_dataset(
    arguments: dict[str, Any],
    dataset: pd.DataFrame | None,
    datasets: dict[str, pd.DataFrame],
    _result: Callable[..., ToolResult],
) -> tuple[pd.DataFrame | None, str, ToolResult | None]:
    """Resolve a dataset or return an error ToolResult.

    Returns ``(active_ds, label, error_result)``.  ``label`` is the
    human-readable dataset name (explicit name, last-loaded key, or
    ``"Dataset"``).  When ``error_result`` is not None the caller should
    return it immediately.
    """
    ds_name = arguments.get("dataset_name")
    active_ds = _resolve_dataset(ds_name, dataset, datasets)
    label = ds_name or (list(datasets.keys())[-1] if datasets else "Dataset")
    if active_ds is not None:
        return active_ds, label, None
    if datasets:
        return (
            None,
            label,
            _result(
                f"Dataset '{ds_name}' not found. Available: {list(datasets.keys())}"
            ),
        )
    return None, label, _result("No dataset loaded. Load data first.")


# ---------------------------------------------------------------------------
# Import handler modules to trigger registration via @_register
# ---------------------------------------------------------------------------

from . import _charts as _charts  # noqa: E402, F401
from . import _data_inspector as _data_inspector  # noqa: E402, F401
from . import _quality_checks as _quality_checks  # noqa: E402, F401
from . import _results_manager as _results_manager  # noqa: E402, F401
from . import _signals_builder as _signals_builder  # noqa: E402, F401
from . import _simulators as _simulators  # noqa: E402, F401
from . import _strategy_runners as _strategy_runners  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------


_CACHEABLE_TOOLS = ("run_strategy", "scan_strategies", "simulate")


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    dataset: pd.DataFrame | None,
    signals: dict[str, pd.DataFrame] | None = None,
    datasets: dict[str, pd.DataFrame] | None = None,
    results: dict[str, dict] | None = None,
    dataset_fingerprint: str | None = None,
    uploaded_files: dict[str, str] | None = None,
) -> ToolResult:
    """
    Execute a tool call and return a ToolResult.

    The ToolResult contains a concise ``llm_summary`` (sent to the LLM) and a
    richer ``user_display`` (shown in the chat UI).  The ``dataset`` field
    carries the currently-active DataFrame forward.  The ``signals`` dict
    carries named signal date DataFrames across tool calls.  The ``datasets``
    dict is the named-dataset registry (ticker/filename -> DataFrame) that
    allows multiple datasets to be active simultaneously.  The ``results`` dict
    is the session-scoped strategy run registry.
    """
    _ensure_plugins_loaded()

    if signals is None:
        signals = {}
    if datasets is None:
        datasets = {}
    if results is None:
        results = {}

    # --- Pydantic validation gate ---
    # Lazy import: _models pulls in pydantic which is an optional UI dep.
    from ._models import TOOL_ARG_MODELS

    model_cls = TOOL_ARG_MODELS.get(tool_name)
    provider = get_provider_for_tool(tool_name)
    if model_cls is None and provider is not None:
        model_cls = provider.get_arg_model(tool_name)
    if model_cls is not None:
        from pydantic import ValidationError

        try:
            validated = model_cls.model_validate(arguments)
            arguments = validated.model_dump(mode="json", exclude_none=True)
        except ValidationError as e:
            items = []
            for err in e.errors():
                loc = ".".join(str(p) for p in err.get("loc", ())) or "<root>"
                items.append(f"{loc}: {err.get('msg', 'invalid value')}")
            error_text = "; ".join(items)
            if len(error_text) > 500:
                error_text = f"{error_text[:497]}..."
            return ToolResult(
                f"Invalid arguments for {tool_name}: {error_text}",
                dataset,
                signals=signals,
                datasets=datasets,
                results=results,
            )

    # Inject internal metadata AFTER validation so Pydantic doesn't strip it.
    if dataset_fingerprint and tool_name in _CACHEABLE_TOOLS:
        arguments = {**arguments, "_dataset_fingerprint": dataset_fingerprint}
    if uploaded_files and tool_name == "load_csv_data":
        arguments = {**arguments, "_uploaded_file_paths": set(uploaded_files.values())}

    # Helper to build a ToolResult that always carries state forward.
    def _result(
        llm_summary: str,
        ds: pd.DataFrame | None = dataset,
        user_display: str | None = None,
        sigs: dict[str, pd.DataFrame] | None = None,
        dss: dict[str, pd.DataFrame] | None = None,
        active_name: str | None = None,
        res: dict[str, dict] | None = None,
        chart_figure: Any = None,
        result_df: pd.DataFrame | None = None,
    ) -> ToolResult:
        return ToolResult(
            llm_summary,
            ds,
            user_display,
            sigs if sigs is not None else signals,
            dss if dss is not None else datasets,
            active_name,
            res if res is not None else results,
            chart_figure=chart_figure,
            result_df=result_df,
        )

    # Check the handler registry first
    handler = _TOOL_HANDLERS.get(tool_name)
    if handler is not None:
        return handler(arguments, dataset, signals, datasets, results, _result)

    # Generic data-provider dispatch (external providers like EODHD)
    if provider is not None:
        try:
            summary, df = provider.execute(tool_name, arguments)
            if df is not None:
                if not provider.replaces_dataset(tool_name):
                    # Display-only tool (e.g. stock prices) — show but keep
                    # the current active dataset unchanged.
                    display = f"{summary}\n\n{_df_to_markdown(df)}"
                    return _result(summary, user_display=display)
                # Derive a label from the ticker symbol in the data if possible.
                label: str
                if "underlying_symbol" in df.columns:
                    syms = df["underlying_symbol"].unique()
                    label = syms[0] if len(syms) == 1 else str(list(syms))
                else:
                    label = tool_name
                updated_datasets = {**datasets, label: df}
                display = f"{summary}\n\nFirst 5 rows:\n{_df_to_markdown(df.head())}"
                if len(updated_datasets) > 1:
                    summary += f"\nActive datasets: {list(updated_datasets.keys())}"
                return _result(
                    summary, df, display, dss=updated_datasets, active_name=label
                )
            return _result(summary)
        except Exception as e:
            return _result(f"Error running {tool_name}: {e}")

    available = list(_TOOL_HANDLERS.keys())
    return _result(f"Unknown tool: {tool_name}. Available: {', '.join(available)}")
