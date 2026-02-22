"""Pydantic v2 models for tool argument validation and schema generation.

Each model corresponds to one tool in the tool registry. Models validate
LLM-generated JSON at the ``execute_tool()`` dispatch boundary and serve
as the single source of truth for OpenAI-compatible tool parameter schemas.

Output models (``StrategyResultSummary``, ``SimulationResultEntry``) type
the lightweight dicts stored in the session results registry.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from ._schemas import SIGNAL_NAMES, STRATEGY_NAMES

# ---------------------------------------------------------------------------
# Shared validator helpers
# ---------------------------------------------------------------------------


def _check_strategy_name(v: str | None) -> str | None:
    """Validate a strategy name against the known registry."""
    if v is not None and v not in STRATEGY_NAMES:
        raise ValueError(
            f"Unknown strategy '{v}'. Available: {', '.join(STRATEGY_NAMES)}"
        )
    return v


def _check_signal_name(v: str | None) -> str | None:
    """Validate a signal name against the known registry."""
    if v is not None and v not in SIGNAL_NAMES:
        raise ValueError(f"Unknown signal '{v}'. Available: {', '.join(SIGNAL_NAMES)}")
    return v


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SlippageModel(str, Enum):
    mid = "mid"
    spread = "spread"
    liquidity = "liquidity"


class ChartType(str, Enum):
    line = "line"
    bar = "bar"
    scatter = "scatter"
    histogram = "histogram"
    heatmap = "heatmap"
    candlestick = "candlestick"


class DataSource(str, Enum):
    dataset = "dataset"
    result = "result"
    simulation = "simulation"
    signal = "signal"
    stock = "stock"


class IndicatorType(str, Enum):
    rsi = "rsi"
    sma = "sma"
    ema = "ema"
    bbands = "bbands"
    macd = "macd"
    volume = "volume"


class SelectorType(str, Enum):
    nearest = "nearest"
    highest_premium = "highest_premium"
    lowest_premium = "lowest_premium"
    first = "first"


class PositionType(str, Enum):
    head = "head"
    tail = "tail"


class CombineMode(str, Enum):
    and_ = "and"
    or_ = "or"


# ---------------------------------------------------------------------------
# Shared mixins
# ---------------------------------------------------------------------------


class StrategyParamsMixin(BaseModel):
    max_entry_dte: int | None = Field(
        None, description="Maximum days to expiration for entry (default: 90)"
    )
    exit_dte: int | None = Field(
        None, description="Days to expiration for exit (default: 0)"
    )
    dte_interval: int | None = Field(
        None, description="Interval size for DTE grouping in stats (default: 7)"
    )
    max_otm_pct: float | None = Field(
        None, description="Maximum out-of-the-money percentage (default: 0.5)"
    )
    otm_pct_interval: float | None = Field(
        None,
        description="Interval size for OTM grouping in stats (default: 0.05)",
    )
    min_bid_ask: float | None = Field(
        None, description="Minimum bid/ask price threshold (default: 0.05)"
    )
    raw: bool | None = Field(
        None,
        description="If true, return raw trades instead of aggregated stats (default: false)",
    )
    drop_nan: bool | None = Field(
        None,
        description="If true, remove NaN rows from output (default: true)",
    )
    slippage: SlippageModel | None = Field(
        None,
        description=(
            "Slippage model: 'mid' (midpoint), 'spread' (full spread), "
            "or 'liquidity' (volume-based). Default: 'mid'"
        ),
    )


class CalendarParamsMixin(BaseModel):
    front_dte_min: int | None = Field(
        None,
        description="Minimum DTE for front (near-term) leg (default: 20)",
    )
    front_dte_max: int | None = Field(
        None,
        description="Maximum DTE for front (near-term) leg (default: 40)",
    )
    back_dte_min: int | None = Field(
        None,
        description="Minimum DTE for back (longer-term) leg (default: 50)",
    )
    back_dte_max: int | None = Field(
        None,
        description="Maximum DTE for back (longer-term) leg (default: 90)",
    )


class SignalMixin(BaseModel):
    entry_signal: str | None = Field(
        None,
        json_schema_extra={"enum": SIGNAL_NAMES},  # type: ignore[dict-item]
        description=(
            "Optional TA signal that gates entry. Only enters trades on "
            "dates where the signal is True for the underlying symbol. "
            "Momentum: macd_cross_above, macd_cross_below, ema_cross_above, ema_cross_below. "
            "Mean-reversion: rsi_below (default RSI<30), rsi_above (default RSI>70), "
            "bb_below_lower, bb_above_upper. "
            "Trend filter: sma_above (default SMA50), sma_below (default SMA50). "
            "Volatility: atr_above (default ATR > 1.5x median), atr_below (default ATR < 0.75x median). "
            "Calendar: day_of_week (default Friday). "
            "Use entry_signal_params to override defaults."
        ),
    )
    entry_signal_params: dict[str, Any] | None = Field(
        None,
        description=(
            "Optional parameters for entry_signal. Keys by signal type: "
            "rsi_below/rsi_above -> {period: int, threshold: float}; "
            "sma_below/sma_above -> {period: int}; "
            "macd_cross_above/macd_cross_below -> {fast: int, slow: int, signal_period: int}; "
            "bb_above_upper/bb_below_lower -> {length: int, std: float}; "
            "ema_cross_above/ema_cross_below -> {fast: int, slow: int}; "
            "atr_above/atr_below -> {period: int, multiplier: float}; "
            "day_of_week -> {days: list[int]} where 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri."
        ),
    )
    entry_signal_days: int | None = Field(
        None,
        ge=1,
        description=(
            "Optional: require the entry_signal to be True for this many consecutive "
            "trading days before entering. Works with any signal. "
            "Omit or set to 1 for single-bar behavior (default)."
        ),
    )
    exit_signal: str | None = Field(
        None,
        json_schema_extra={"enum": SIGNAL_NAMES},  # type: ignore[dict-item]
        description=(
            "Optional TA signal that gates exit. Only exits trades on "
            "dates where the signal is True. Same signal names as entry_signal."
        ),
    )
    exit_signal_params: dict[str, Any] | None = Field(
        None,
        description=(
            "Optional parameters for exit_signal. Same keys as entry_signal_params."
        ),
    )
    exit_signal_days: int | None = Field(
        None,
        ge=1,
        description=(
            "Optional: require the exit_signal condition to hold for this "
            "many consecutive trading days before exiting. Works the same as "
            "entry_signal_days but for the exit signal. "
            "Omit or set to 1 for no sustained requirement (default behavior)."
        ),
    )
    entry_signal_slot: str | None = Field(
        None,
        description=(
            "Name of a pre-built signal slot (from build_signal) to "
            "use as entry date filter. Use this for composite signals. "
            "Cannot be combined with entry_signal."
        ),
    )
    exit_signal_slot: str | None = Field(
        None,
        description=(
            "Name of a pre-built signal slot (from build_signal) to "
            "use as exit date filter. Use this for composite signals. "
            "Cannot be combined with exit_signal."
        ),
    )

    @field_validator("entry_signal", "exit_signal", mode="before")
    @classmethod
    def _validate_signal_name(cls, v: str | None) -> str | None:
        return _check_signal_name(v)


# ---------------------------------------------------------------------------
# Input models — one per tool
# ---------------------------------------------------------------------------


class PreviewDataArgs(BaseModel):
    dataset_name: str | None = Field(
        None,
        description=(
            "Name (ticker or filename) of the dataset to preview. "
            "Omit to use the most-recently-loaded dataset."
        ),
    )
    rows: int | None = Field(
        None,
        ge=1,
        description="Number of rows to show (default: 5)",
    )
    position: PositionType | None = Field(
        None, description="Show first or last rows (default: head)"
    )
    sample: bool | None = Field(
        None, description="If true, show random sample instead of head/tail"
    )


class DescribeDataArgs(BaseModel):
    dataset_name: str | None = Field(
        None, description="Dataset to describe. Omit for most recent."
    )
    columns: list[str] | None = Field(
        None, description="Specific columns to describe. Omit for all."
    )


class SuggestStrategyParamsArgs(BaseModel):
    dataset_name: str | None = Field(
        None,
        description=(
            "Dataset to analyze. Omit to use the most-recently-loaded dataset."
        ),
    )
    strategy_name: str | None = Field(
        None,
        json_schema_extra={"enum": STRATEGY_NAMES},  # type: ignore[dict-item]
        description=(
            "Optional: tailor suggestions for a specific strategy. "
            "Iron condors and multi-leg strategies get tighter DTE/OTM% "
            "defaults. Calendar strategies receive front/back DTE "
            "recommendations instead of max_entry_dte."
        ),
    )

    @field_validator("strategy_name", mode="before")
    @classmethod
    def _validate_strategy_name(cls, v: str | None) -> str | None:
        return _check_strategy_name(v)


class RunStrategyArgs(SignalMixin, StrategyParamsMixin, CalendarParamsMixin):
    strategy_name: str = Field(
        ...,
        json_schema_extra={"enum": STRATEGY_NAMES},  # type: ignore[dict-item]
        description="Name of the strategy to run",
    )
    dataset_name: str | None = Field(
        None,
        description=(
            "Name (ticker or filename) of the dataset to run the "
            "strategy on. Omit to use the most-recently-loaded dataset. "
            "Use this to compare the same strategy across multiple "
            "loaded datasets (e.g. 'SPY' vs 'QQQ')."
        ),
    )

    @field_validator("strategy_name", mode="before")
    @classmethod
    def _validate_strategy_name(cls, v: str) -> str:
        return _check_strategy_name(v)  # type: ignore[return-value]


class ScanStrategiesArgs(BaseModel):
    strategy_names: list[str] = Field(
        ...,
        min_length=1,
        json_schema_extra={
            "items": {"type": "string", "enum": STRATEGY_NAMES},  # type: ignore[dict-item]
        },
        description="One or more strategy names to include in the scan.",
    )
    dataset_name: str | None = Field(
        None,
        description=(
            "Dataset to run on. Omit to use the most-recently-loaded dataset."
        ),
    )
    max_entry_dte_values: list[int] | None = Field(
        None,
        description=(
            "List of max_entry_dte values to sweep (e.g. [30, 45, 60]). "
            "Omit to use the default (90)."
        ),
    )
    exit_dte_values: list[int] | None = Field(
        None,
        description=(
            "List of exit_dte values to sweep (e.g. [0, 7, 14]). "
            "Omit to use the default (0)."
        ),
    )
    max_otm_pct_values: list[float] | None = Field(
        None,
        description=(
            "List of max_otm_pct values to sweep (e.g. [0.1, 0.2, 0.3]). "
            "Omit to use the default (0.5)."
        ),
    )
    slippage: SlippageModel | None = Field(
        None,
        description=("Slippage model applied to all combinations. Default: 'mid'."),
    )
    max_combinations: int | None = Field(
        None,
        description=(
            "Safety cap on total combinations to run (default: 50). "
            "Combinations exceeding this limit are skipped."
        ),
    )

    @field_validator("strategy_names", mode="before")
    @classmethod
    def _validate_strategy_names(cls, v: list[str]) -> list[str]:
        if isinstance(v, list):
            invalid = [s for s in v if s not in STRATEGY_NAMES]
            if invalid:
                msg = f"Unknown strategies: {invalid}. Available: {', '.join(STRATEGY_NAMES)}"
                raise ValueError(msg)
        return v


class SignalSpec(BaseModel):
    name: str = Field(
        ...,
        json_schema_extra={"enum": SIGNAL_NAMES},  # type: ignore[dict-item]
        description="Signal type name",
    )
    params: dict[str, Any] | None = Field(
        None, description="Optional parameter overrides for this signal"
    )
    days: int | None = Field(
        None,
        ge=1,
        description=(
            "Optional: require signal True for N consecutive days (sustained)"
        ),
    )

    @field_validator("name", mode="before")
    @classmethod
    def _validate_signal_name(cls, v: str) -> str:
        return _check_signal_name(v)  # type: ignore[return-value]


class BuildSignalArgs(BaseModel):
    slot: str = Field(
        ...,
        description=(
            "Name for this signal (e.g. 'entry', 'exit', "
            "'oversold_uptrend'). Used to reference the signal "
            "in run_strategy or combine with other slots."
        ),
    )
    signals: list[SignalSpec] = Field(
        ...,
        min_length=1,
        description="One or more signals to combine (default: AND)",
    )
    combine: CombineMode | None = Field(
        None,
        description=(
            "How to combine multiple signals: 'and' (all must be True, "
            "default) or 'or' (any must be True)"
        ),
    )
    dataset_name: str | None = Field(
        None,
        description=(
            "Name (ticker or filename) of the dataset to build the "
            "signal from. Omit to use the most-recently-loaded dataset."
        ),
    )


class PreviewSignalArgs(BaseModel):
    slot: str = Field(..., description="Signal slot name to preview")


class ListSignalsArgs(BaseModel):
    pass


class ListResultsArgs(BaseModel):
    strategy_name: str | None = Field(
        None,
        json_schema_extra={"enum": STRATEGY_NAMES},  # type: ignore[dict-item]
        description=("Optional: filter to only show runs for this strategy."),
    )

    @field_validator("strategy_name", mode="before")
    @classmethod
    def _validate_strategy_name(cls, v: str | None) -> str | None:
        return _check_strategy_name(v)


class InspectCacheArgs(BaseModel):
    symbol: str | None = Field(
        None,
        description=(
            "Optional ticker symbol to filter results (e.g. 'SPY'). "
            "Omit to list all cached symbols."
        ),
    )


class ClearCacheArgs(BaseModel):
    symbol: str | None = Field(
        None,
        description="Ticker to clear (e.g. 'SPY'). Omit to clear all.",
    )


class FetchStockDataArgs(BaseModel):
    symbol: str = Field(..., description="US stock ticker symbol (e.g. SPY, AAPL, QQQ)")


class IndicatorSpec(BaseModel):
    type: IndicatorType = Field(...)
    period: int | None = None
    std: float | None = None
    fast: int | None = None
    slow: int | None = None
    signal: int | None = None


class CreateChartArgs(BaseModel):
    chart_type: ChartType = Field(
        ...,
        description=(
            "Type of chart: 'line' for time series/equity curves, "
            "'bar' for comparisons, 'scatter' for correlation plots, "
            "'histogram' for return distributions, "
            "'heatmap' for 2D aggregated grids, "
            "'candlestick' for OHLC stock price charts."
        ),
    )
    data_source: DataSource = Field(
        ...,
        description=(
            "Where to pull data from: 'dataset' (active or named "
            "dataset), 'result' (strategy run summary from results registry), "
            "'simulation' (trade log from a simulation run), "
            "'signal' (signal slot dates), "
            "'stock' (cached OHLCV stock data from fetch_stock_data)."
        ),
    )
    x: str | None = Field(None, description="Column name for the x-axis.")
    y: str | None = Field(None, description="Column name for the y-axis.")
    heatmap_col: str | None = Field(
        None,
        description=(
            "Column name for heatmap cell values (aggregated with mean). "
            "Required only for heatmap chart_type."
        ),
    )
    xlabel: str | None = Field(
        None, description="X-axis label. Defaults to column name."
    )
    ylabel: str | None = Field(
        None, description="Y-axis label. Defaults to column name."
    )
    result_key: str | None = Field(
        None,
        description=(
            "Key of a strategy result to chart (from list_results). "
            "Only used when data_source='result'. Omit for most recent."
        ),
    )
    simulation_key: str | None = Field(
        None,
        description=(
            "Key of a simulation to chart. Only used when "
            "data_source='simulation'. Omit for most recent."
        ),
    )
    signal_slot: str | None = Field(
        None,
        description=("Signal slot name. Only used when data_source='signal'."),
    )
    dataset_name: str | None = Field(
        None,
        description=(
            "Name of a specific dataset (ticker or filename). "
            "Used with data_source='dataset'. Omit to use the "
            "most-recently-loaded dataset."
        ),
    )
    symbol: str | None = Field(
        None,
        description=(
            "Stock ticker symbol (e.g. 'SPY'). Required when data_source='stock'."
        ),
    )
    indicators: list[IndicatorSpec] | None = Field(
        None,
        description=("Technical indicators to overlay or add as subplots."),
    )
    bins: int | None = Field(
        None, description="Number of bins for histogram. Omit for auto."
    )
    color: str | None = Field(
        None,
        description="Color for the chart traces (e.g. 'blue', '#1f77b4').",
    )
    figsize_width: int | None = Field(
        None, description="Chart width in pixels (default: 800)."
    )
    figsize_height: int | None = Field(
        None, description="Chart height in pixels (default: 500)."
    )


class SimulateArgs(SignalMixin, StrategyParamsMixin, CalendarParamsMixin):
    strategy_name: str = Field(
        ...,
        json_schema_extra={"enum": STRATEGY_NAMES},  # type: ignore[dict-item]
        description="Name of the strategy to simulate",
    )
    capital: float | None = Field(
        None, description="Starting capital in dollars (default: 100000)"
    )
    quantity: int | None = Field(
        None,
        ge=1,
        description="Number of contracts per trade (default: 1)",
    )
    max_positions: int | None = Field(
        None,
        ge=1,
        description="Maximum concurrent open positions (default: 1)",
    )
    multiplier: int | None = Field(
        None,
        ge=1,
        description="Contract multiplier (default: 100)",
    )
    selector: SelectorType | None = Field(
        None,
        description=(
            "How to pick one trade when multiple candidates exist for a date. "
            "'nearest' = closest to ATM, 'highest_premium' = most credit, "
            "'lowest_premium' = cheapest debit, 'first' = first row. "
            "Default: 'nearest'."
        ),
    )
    dataset_name: str | None = Field(
        None,
        description=(
            "Name of the dataset to simulate on. "
            "Omit to use the most-recently-loaded dataset."
        ),
    )
    # Simulate does not use 'raw' — override to reject it explicitly.
    # exclude=True removes it from model_dump(); json_schema_extra hides it
    # from model_json_schema() so the LLM tool schema won't expose it.
    raw: bool | None = Field(
        None,
        exclude=True,
        json_schema_extra={"hidden": True},
    )

    @field_validator("strategy_name", mode="before")
    @classmethod
    def _validate_strategy_name(cls, v: str) -> str:
        return _check_strategy_name(v)  # type: ignore[return-value]

    @field_validator("raw", mode="before")
    @classmethod
    def _reject_raw(cls, v: bool | None) -> None:
        if v is not None:
            raise ValueError(
                "simulate does not support the 'raw' parameter. "
                "Use run_strategy with raw=true to see individual trades."
            )
        return None


class GetSimulationTradesArgs(BaseModel):
    simulation_key: str | None = Field(
        None,
        description=(
            "Key of the simulation result to retrieve. "
            "Omit to use the most recent simulation."
        ),
    )


class FetchOptionsDataArgs(BaseModel):
    symbol: str = Field(
        ...,
        description="US stock ticker symbol (e.g. AAPL, SPY, TSLA)",
    )
    start_date: str | None = Field(
        None,
        description="Start date (YYYY-MM-DD). Defaults to all available.",
    )
    end_date: str | None = Field(
        None,
        description="End date (YYYY-MM-DD). Defaults to today.",
    )
    option_type: Literal["call", "put"] | None = Field(
        None,
        description="Filter by option type. Omit for both.",
    )
    expiration_type: Literal["monthly", "weekly"] | None = Field(
        None,
        description=(
            "Filter by expiration cycle. Defaults to 'monthly'. "
            "Use 'weekly' for weekly expirations."
        ),
    )


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class StrategyResultSummary(BaseModel):
    strategy: str
    max_entry_dte: int = 90
    exit_dte: int = 0
    max_otm_pct: float = 0.5
    slippage: str = "mid"
    dataset: str = "default"
    count: int = 0
    mean_return: float | None = None
    std: float | None = None
    win_rate: float | None = None


class SimulationResultEntry(BaseModel):
    type: Literal["simulation"] = "simulation"
    strategy: str
    summary: dict[str, Any]


# ---------------------------------------------------------------------------
# Tool argument model registry
# ---------------------------------------------------------------------------

TOOL_ARG_MODELS: dict[str, type[BaseModel]] = {
    "preview_data": PreviewDataArgs,
    "describe_data": DescribeDataArgs,
    "suggest_strategy_params": SuggestStrategyParamsArgs,
    "run_strategy": RunStrategyArgs,
    "scan_strategies": ScanStrategiesArgs,
    "build_signal": BuildSignalArgs,
    "preview_signal": PreviewSignalArgs,
    "list_signals": ListSignalsArgs,
    "list_results": ListResultsArgs,
    "inspect_cache": InspectCacheArgs,
    "clear_cache": ClearCacheArgs,
    "fetch_stock_data": FetchStockDataArgs,
    "create_chart": CreateChartArgs,
    "simulate": SimulateArgs,
    "get_simulation_trades": GetSimulationTradesArgs,
    "fetch_options_data": FetchOptionsDataArgs,
}


# ---------------------------------------------------------------------------
# Schema generation helper
# ---------------------------------------------------------------------------


def _resolve_refs(schema: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    """Recursively resolve ``$ref`` pointers in a JSON schema."""
    if "$ref" in schema:
        ref_path = schema["$ref"]
        # Handle "#/$defs/Foo" format
        ref_name = ref_path.rsplit("/", 1)[-1]
        resolved = defs.get(ref_name, {})
        return _resolve_refs(dict(resolved), defs)

    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key in ("$defs", "definitions"):
            continue
        if isinstance(value, dict):
            result[key] = _resolve_refs(value, defs)
        elif isinstance(value, list):
            result[key] = list(
                _resolve_refs(item, defs) if isinstance(item, dict) else item
                for item in value
            )
        else:
            result[key] = value
    return result


def _strip_titles(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove ``title`` keys that Pydantic adds to every property."""
    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "title":
            continue
        if isinstance(value, dict):
            result[key] = _strip_titles(value)
        elif isinstance(value, list):
            result[key] = list(
                _strip_titles(item) if isinstance(item, dict) else item
                for item in value
            )
        else:
            result[key] = value
    return result


def pydantic_to_openai_params(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Convert a Pydantic v2 model to an OpenAI-compatible parameters dict.

    Resolves ``$ref``/``$defs``, strips ``title`` keys, and ensures
    ``required`` is present.
    """
    raw = model_cls.model_json_schema()
    defs = raw.get("$defs", raw.get("definitions", {}))
    resolved = _resolve_refs(raw, defs)
    cleaned = _strip_titles(resolved)

    # Remove properties marked with json_schema_extra={"hidden": True}
    # (e.g. SimulateArgs.raw which is excluded from model_dump but would
    # otherwise appear in the schema, confusing LLMs).
    props = cleaned.get("properties", {})
    hidden = [k for k, v in props.items() if isinstance(v, dict) and v.get("hidden")]
    for k in hidden:
        del props[k]
    req = cleaned.get("required", [])
    if hidden and req:
        cleaned["required"] = [r for r in req if r not in hidden]

    # Ensure 'required' key exists
    if "required" not in cleaned:
        cleaned["required"] = []

    # Ensure top-level type is "object"
    cleaned.setdefault("type", "object")

    return cleaned
