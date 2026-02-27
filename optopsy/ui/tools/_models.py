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

from pydantic import BaseModel, Field, field_validator, model_validator

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
    per_leg = "per_leg"


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
    results = "results"
    simulation = "simulation"
    signal = "signal"
    stock = "stock"


class BarMode(str, Enum):
    group = "group"
    stack = "stack"


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


class DeltaTarget(BaseModel):
    """Per-leg delta target with min/max range. All values are in the (0, 1] range."""

    model_config = {"extra": "forbid"}

    target: float = Field(
        ...,
        gt=0,
        le=1,
        description="Target absolute delta in the (0, 1] range (e.g. 0.30)",
    )
    min: float = Field(
        ...,
        gt=0,
        le=1,
        description="Minimum absolute delta in the (0, 1] range (e.g. 0.20)",
    )
    max: float = Field(
        ...,
        gt=0,
        le=1,
        description="Maximum absolute delta in the (0, 1] range (e.g. 0.40)",
    )

    @model_validator(mode="after")
    def _check_range_order(self) -> DeltaTarget:
        if self.min > self.target:
            raise ValueError(f"min ({self.min}) must be <= target ({self.target})")
        if self.target > self.max:
            raise ValueError(f"target ({self.target}) must be <= max ({self.max})")
        return self


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
    min_bid_ask: float | None = Field(
        None, description="Minimum bid/ask price threshold (default: 0.05)"
    )
    leg1_delta: DeltaTarget | None = Field(
        None,
        description=(
            "Delta target for leg 1: {target, min, max} with unsigned values 0-1. "
            "Each strategy has sensible defaults. Singles: 0.30 (0.20-0.40). "
            "Straddles: 0.50 (0.40-0.60). Spreads leg1: 0.50 (0.40-0.60). "
            "Iron condor leg1: 0.10 (0.05-0.20). Butterfly leg1: 0.40 (0.30-0.50). "
            "Covered call leg1: 0.80 (0.60-0.95)."
        ),
    )
    leg2_delta: DeltaTarget | None = Field(
        None,
        description=(
            "Delta target for leg 2 (multi-leg strategies only). "
            "Spreads leg2: 0.10 (0.05-0.20). Strangles: 0.30 (0.20-0.40). "
            "Iron condor leg2: 0.30 (0.20-0.40). Butterfly leg2: 0.50 (0.40-0.60)."
        ),
    )
    leg3_delta: DeltaTarget | None = Field(
        None,
        description=(
            "Delta target for leg 3 (3+ leg strategies only). "
            "Butterfly leg3: 0.10 (0.05-0.20). Iron condor leg3: 0.30 (0.20-0.40)."
        ),
    )
    leg4_delta: DeltaTarget | None = Field(
        None,
        description=(
            "Delta target for leg 4 (4-leg strategies only). "
            "Iron condor leg4: 0.10 (0.05-0.20). Iron butterfly leg4: 0.10 (0.05-0.20)."
        ),
    )
    delta_interval: float | None = Field(
        None,
        gt=0,
        le=1,
        description=(
            "Interval size for delta grouping in aggregated stats (default: 0.05). "
            "Controls the width of delta_range buckets in output."
        ),
    )
    stop_loss: float | None = Field(
        None,
        lt=0,
        description=(
            "Early exit stop-loss threshold as a negative decimal "
            "(e.g. -0.5 = exit if trade loses 50%). Omit for no stop-loss."
        ),
    )
    take_profit: float | None = Field(
        None,
        gt=0,
        description=(
            "Early exit take-profit threshold as a positive decimal "
            "(e.g. 0.5 = exit if trade gains 50%). Omit for no take-profit."
        ),
    )
    max_hold_days: int | None = Field(
        None,
        gt=0,
        description=(
            "Maximum holding period in calendar days. Exit after this many days "
            "regardless of DTE or P&L. Omit for no time-based exit."
        ),
    )
    commission: float | None = Field(
        None,
        ge=0,
        description=(
            "Commission per contract in dollars (e.g. 0.65). "
            "Applied to each leg at entry and exit. Omit for no commissions."
        ),
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
            "'liquidity' (volume-based), or 'per_leg' (scales with leg count). Default: 'mid'"
        ),
    )
    per_leg_slippage: float | None = Field(
        None,
        description=(
            "Additive penalty per additional leg for per_leg slippage mode (default: 0.073)"
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
        json_schema_extra={"enum": SIGNAL_NAMES},
        description=(
            "Optional TA signal that gates entry. Only enters trades on "
            "dates where the signal is True for the underlying symbol. "
            "Momentum: macd_cross_above, macd_cross_below, ema_cross_above, ema_cross_below. "
            "Mean-reversion: rsi_below (default RSI<30), rsi_above (default RSI>70), "
            "bb_below_lower, bb_above_upper. "
            "Trend filter: sma_above (default SMA50), sma_below (default SMA50). "
            "Volatility: atr_above (default ATR > 1.5x median), atr_below (default ATR < 0.75x median). "
            "IV rank: iv_rank_above (default >0.5), iv_rank_below (default <0.5) — "
            "percentile of ATM IV vs trailing 252-day range. Requires dataset with implied_volatility. "
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
            "iv_rank_above/iv_rank_below -> {threshold: float, window: int}; "
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
        json_schema_extra={"enum": SIGNAL_NAMES},
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


class LoadCsvDataArgs(BaseModel):
    file_path: str = Field(
        ...,
        description="Path to the CSV file (provided in the upload context).",
    )
    underlying_symbol: int = Field(
        0, ge=0, description="Column index for the underlying symbol."
    )
    underlying_price: int | None = Field(
        None,
        ge=0,
        description="Column index for underlying price. Omit if the CSV does not have this column.",
    )
    option_type: int = Field(
        1, ge=0, description="Column index for option type (call/put)."
    )
    expiration: int = Field(2, ge=0, description="Column index for expiration date.")
    quote_date: int = Field(3, ge=0, description="Column index for quote date.")
    strike: int = Field(4, ge=0, description="Column index for strike price.")
    bid: int = Field(5, ge=0, description="Column index for bid price.")
    ask: int = Field(6, ge=0, description="Column index for ask price.")
    delta: int = Field(
        7,
        ge=0,
        description="Column index for delta Greek. Required for all strategies.",
    )
    gamma: int | None = Field(
        None, ge=0, description="Optional column index for gamma."
    )
    theta: int | None = Field(
        None, ge=0, description="Optional column index for theta."
    )
    vega: int | None = Field(None, ge=0, description="Optional column index for vega.")
    implied_volatility: int | None = Field(
        None, ge=0, description="Optional column index for implied volatility."
    )
    volume: int | None = Field(
        None, ge=0, description="Optional column index for trading volume."
    )
    open_interest: int | None = Field(
        None, ge=0, description="Optional column index for open interest."
    )
    start_date: str | None = Field(
        None, description="Optional start date filter (YYYY-MM-DD)."
    )
    end_date: str | None = Field(
        None, description="Optional end date filter (YYYY-MM-DD)."
    )


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
        json_schema_extra={"enum": STRATEGY_NAMES},
        description=(
            "Optional: tailor suggestions for a specific strategy. "
            "Iron condors and multi-leg strategies get tighter DTE "
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
        json_schema_extra={"enum": STRATEGY_NAMES},
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
            "items": {"type": "string", "enum": STRATEGY_NAMES},
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
        json_schema_extra={"enum": SIGNAL_NAMES},
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


class BuildCustomSignalArgs(BaseModel):
    slot: str = Field(
        ...,
        description=(
            "Name for this custom signal slot (e.g. 'gap_up', 'volume_spike'). "
            "Used to reference the signal in run_strategy via entry_signal_slot / "
            "exit_signal_slot."
        ),
    )
    code: str = Field(
        ...,
        description=(
            "Python code that computes a boolean Series named `signal` from an "
            "OHLCV DataFrame `df`. Available columns: underlying_symbol, "
            "quote_date, open, high, low, close, volume. Code runs per symbol "
            "group with `pd` (pandas) and `np` (numpy) available.\n\n"
            "Examples:\n"
            "- Gap up 2%: signal = df['open'] > df['close'].shift(1) * 1.02\n"
            "- Volume spike 3x 20d avg: signal = df['volume'] > df['volume'].rolling(20).mean() * 3\n"
            "- Close crosses above 200-day high: signal = df['close'] > df['high'].rolling(200).max().shift(1)\n"
            "- Inside day: signal = (df['high'] < df['high'].shift(1)) & (df['low'] > df['low'].shift(1))"
        ),
    )
    description: str | None = Field(
        None,
        description="Human-readable description of the custom signal logic.",
    )
    dataset_name: str | None = Field(
        None,
        description=(
            "Name (ticker or filename) of the dataset to build the signal from. "
            "Omit to use the most-recently-loaded dataset."
        ),
    )


class PreviewSignalArgs(BaseModel):
    slot: str = Field(..., description="Signal slot name to preview")


class ListSignalsArgs(BaseModel):
    pass


class ListResultsArgs(BaseModel):
    strategy_name: str | None = Field(
        None,
        json_schema_extra={"enum": STRATEGY_NAMES},
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
            "dataset), 'result' (single strategy run summary), "
            "'results' (all session results as a multi-row DataFrame "
            "for comparison charting — use with result_keys to filter), "
            "'simulation' (trade log from a simulation run), "
            "'signal' (signal slot dates), "
            "'stock' (cached OHLCV stock data from fetch_stock_data)."
        ),
    )
    x: str | None = Field(None, description="Column name for the x-axis.")
    y: str | None = Field(None, description="Column name for the y-axis.")
    y_columns: list[str] | None = Field(
        None,
        description=(
            "Multiple y-axis columns to plot as separate traces. "
            "Use instead of 'y' when comparing metrics side by side. "
            "Cannot be combined with 'y'."
        ),
    )
    group_by: str | None = Field(
        None,
        description=(
            "Column to group data by. Creates one trace per unique value. "
            "For example, group_by='strategy' with x='max_entry_dte' and "
            "y='mean_return' creates one bar per strategy per bucket."
        ),
    )
    bar_mode: BarMode | None = Field(
        None,
        description=(
            "Bar chart layout mode: 'group' (side by side, default) "
            "or 'stack' (stacked). Only applies to bar charts with "
            "multiple traces."
        ),
    )
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
    result_keys: list[str] | None = Field(
        None,
        description=(
            "List of result keys to include when data_source='results'. "
            "Omit to include all results in the session."
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
        json_schema_extra={"enum": STRATEGY_NAMES},
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


class CompareResultsArgs(BaseModel):
    result_keys: list[str] | None = Field(
        None,
        description=(
            "List of result keys to compare (from list_results). "
            "Omit to compare all results in this session."
        ),
    )
    sort_by: str | None = Field(
        None,
        description=(
            "Metric to sort by: 'mean_return', 'win_rate', 'sharpe', "
            "'max_drawdown', 'profit_factor', or 'count'. "
            "Default: 'mean_return'."
        ),
    )
    include_chart: bool | None = Field(
        None,
        description=(
            "If true, attach a grouped bar chart comparing key metrics "
            "across results. Default: true."
        ),
    )


class GetSimulationTradesArgs(BaseModel):
    simulation_key: str | None = Field(
        None,
        description=(
            "Key of the simulation result to retrieve. "
            "Omit to use the most recent simulation."
        ),
    )


class FilterOp(str, Enum):
    gt = "gt"
    lt = "lt"
    eq = "eq"
    gte = "gte"
    lte = "lte"
    contains = "contains"


class QueryResultsArgs(BaseModel):
    result_key: str | None = Field(
        None,
        description=(
            "Display key from list_results (e.g. 'long_calls:dte=45,exit=0,...'). "
            "Omit to list all available result keys with summaries."
        ),
    )
    sort_by: str | None = Field(
        None,
        description="Column name to sort by (e.g. 'mean', 'pct_change', 'count').",
    )
    ascending: bool | None = Field(
        None,
        description="Sort ascending (default: false = descending).",
    )
    head: int | None = Field(
        None,
        ge=1,
        description="Return only the first N rows after sorting/filtering.",
    )
    filter_column: str | None = Field(
        None,
        description="Column to filter on.",
    )
    filter_op: FilterOp | None = Field(
        None,
        description="Filter operation: gt, lt, eq, gte, lte, contains.",
    )
    filter_value: str | None = Field(
        None,
        description="Value to filter against (will be cast to column dtype).",
    )
    columns: list[str] | None = Field(
        None,
        description="Select specific columns to return. Omit for all.",
    )


class CheckDataQualityArgs(BaseModel):
    dataset_name: str | None = Field(
        None,
        description=("Dataset to check. Omit to use the most-recently-loaded dataset."),
    )
    strategy_name: str | None = Field(
        None,
        json_schema_extra={"enum": STRATEGY_NAMES},
        description=(
            "Optional: tailor checks for a specific strategy. "
            "Adds option-type balance, strike density, and "
            "expiration coverage checks relevant to the strategy."
        ),
    )

    @field_validator("strategy_name", mode="before")
    @classmethod
    def _validate_strategy_name(cls, v: str | None) -> str | None:
        return _check_strategy_name(v)


class DownloadOptionsDataArgs(BaseModel):
    symbol: str = Field(
        ...,
        description="US stock ticker symbol (e.g. SPY, AAPL, TSLA)",
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
        description="End date (YYYY-MM-DD). Defaults to all available.",
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
    slippage: str = "mid"
    dataset: str = "default"
    count: int = 0
    mean_return: float | None = None
    std: float | None = None
    win_rate: float | None = None
    profit_factor: float | None = None


class SimulationResultEntry(BaseModel):
    type: Literal["simulation"] = "simulation"
    strategy: str
    summary: dict[str, Any]


# ---------------------------------------------------------------------------
# IV surface tool models
# ---------------------------------------------------------------------------


class PlotVolSurfaceArgs(BaseModel):
    dataset_name: str | None = Field(
        None,
        description="Dataset to use. Omit for most recent.",
    )
    quote_date: str | None = Field(
        None,
        description=(
            "Date (YYYY-MM-DD) to show the surface for. "
            "Omit for the latest date in the dataset."
        ),
    )
    option_type: Literal["call", "put"] = Field(
        "call",
        description="Option type to plot. Default: 'call'.",
    )
    figsize_width: int | None = Field(
        None, description="Chart width in pixels (default: 900)."
    )
    figsize_height: int | None = Field(
        None, description="Chart height in pixels (default: 600)."
    )


class IVTermStructureArgs(BaseModel):
    dataset_name: str | None = Field(
        None,
        description="Dataset to use. Omit for most recent.",
    )
    quote_date: str | None = Field(
        None,
        description=(
            "Date (YYYY-MM-DD) to show the term structure for. "
            "Omit for the latest date in the dataset."
        ),
    )
    figsize_width: int | None = Field(
        None, description="Chart width in pixels (default: 800)."
    )
    figsize_height: int | None = Field(
        None, description="Chart height in pixels (default: 500)."
    )


class SummarizeSessionArgs(BaseModel):
    """No arguments required — summarizes all session state."""


# ---------------------------------------------------------------------------
# Tool argument model registry
# ---------------------------------------------------------------------------

TOOL_ARG_MODELS: dict[str, type[BaseModel]] = {
    "load_csv_data": LoadCsvDataArgs,
    "preview_data": PreviewDataArgs,
    "describe_data": DescribeDataArgs,
    "suggest_strategy_params": SuggestStrategyParamsArgs,
    "run_strategy": RunStrategyArgs,
    "scan_strategies": ScanStrategiesArgs,
    "build_signal": BuildSignalArgs,
    "build_custom_signal": BuildCustomSignalArgs,
    "preview_signal": PreviewSignalArgs,
    "list_signals": ListSignalsArgs,
    "list_results": ListResultsArgs,
    "inspect_cache": InspectCacheArgs,
    "clear_cache": ClearCacheArgs,
    "fetch_stock_data": FetchStockDataArgs,
    "compare_results": CompareResultsArgs,
    "query_results": QueryResultsArgs,
    "create_chart": CreateChartArgs,
    "plot_vol_surface": PlotVolSurfaceArgs,
    "iv_term_structure": IVTermStructureArgs,
    "simulate": SimulateArgs,
    "get_simulation_trades": GetSimulationTradesArgs,
    "check_data_quality": CheckDataQualityArgs,
    "download_options_data": DownloadOptionsDataArgs,
    "fetch_options_data": FetchOptionsDataArgs,
    "summarize_session": SummarizeSessionArgs,
}


# ---------------------------------------------------------------------------
# Schema generation helper
# ---------------------------------------------------------------------------


def _resolve_refs(schema: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    """Recursively resolve ``$ref`` pointers in a JSON schema.

    Pydantic v2's ``model_json_schema()`` emits shared sub-models (enums,
    nested BaseModels) as ``$defs`` entries referenced via ``$ref`` pointers.
    OpenAI's function-calling schema format does not support ``$ref``, so this
    function inlines every reference by walking the schema tree depth-first.
    """
    if "$ref" in schema:
        ref_path = schema["$ref"]
        # Extract the definition name from "#/$defs/Foo" or "#/definitions/Foo"
        ref_name = ref_path.rsplit("/", 1)[-1]
        resolved = defs.get(ref_name, {})
        # Recurse in case the resolved definition itself contains $ref pointers
        return _resolve_refs(dict(resolved), defs)

    result: dict[str, Any] = {}
    for key, value in schema.items():
        # Drop the $defs / definitions block itself — its contents are inlined
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
