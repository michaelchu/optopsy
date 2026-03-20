# Tier 1 Quant Analytics Implementation Plan

## Overview

Add three new analytics modules for idea generation in options backtesting:

1. **Variance Risk Premium (VRP)** — RV vs IV comparison
2. **Volatility Skew Analytics** — strike-level IV analysis
3. **Volatility Cone** — historical RV percentiles across tenors

These live in a new `optopsy/volatility.py` module (DataFrame-in, DataFrame-out analytics) with corresponding signals in `optopsy/signals/iv.py` and UI tools in `optopsy/ui/tools/_volatility.py`.

---

## 1. New Module: `optopsy/volatility.py`

Core analytics functions that return DataFrames (not signals, not scalar metrics). These are the "research tools" a quant uses to explore vol dynamics before committing to a strategy.

### 1a. Variance Risk Premium

```python
def variance_risk_premium(
    options_data: pd.DataFrame,
    stock_data: pd.DataFrame,
    rv_windows: list[int] | None = None,   # default [10, 21, 63]
    annualize: bool = True,
    trading_days: int = 252,
) -> pd.DataFrame:
    """Compare ATM implied volatility to realized volatility.

    Returns per (symbol, quote_date):
      - atm_iv: ATM implied vol (annualized)
      - rv_{N}d: realized vol for each window (close-to-close, annualized)
      - vrp_{N}d: IV - RV (positive = vol is expensive = edge for sellers)

    Input:
      - options_data: must have implied_volatility, strike, close columns
      - stock_data: must have underlying_symbol, quote_date, close
    """
```

**Implementation:**
- Reuse `_compute_atm_iv()` from `signals/iv.py` for ATM IV extraction
- Compute RV as `std(log_returns, window) * sqrt(252)` from stock close prices
- Merge on `(underlying_symbol, quote_date)` and compute VRP = IV - RV
- Multiple windows let the user see short-term vs medium-term RV

### 1b. Volatility Skew

```python
def volatility_skew(
    options_data: pd.DataFrame,
    delta_levels: list[float] | None = None,  # default [0.25, 0.50, 0.75]
    dte_range: tuple[int, int] = (20, 60),
) -> pd.DataFrame:
    """Compute IV skew metrics per (symbol, quote_date).

    Returns:
      - iv_25d_put, iv_50d, iv_25d_call: IV at each delta level
      - skew_25d: 25d put IV - 25d call IV (positive = put skew)
      - risk_reversal: 25d call IV - 25d put IV
      - butterfly_25d: (25d put IV + 25d call IV) / 2 - 50d IV (smile convexity)

    Input:
      - options_data: must have delta, implied_volatility, option_type, expiration, quote_date
    """
```

**Implementation:**
- Filter to DTE range to get a consistent tenor
- For each `(symbol, quote_date)`, find options closest to each delta level
- Calls use positive delta, puts use negative delta (abs value matching)
- Interpolate IV at exact delta targets via nearest-neighbor (simple) or linear interp between two closest strikes
- Compute skew = 25d put IV - 25d call IV, risk reversal, butterfly spread

### 1c. Volatility Cone

```python
def volatility_cone(
    stock_data: pd.DataFrame,
    windows: list[int] | None = None,  # default [10, 21, 42, 63, 126, 252]
    percentiles: list[float] | None = None,  # default [10, 25, 50, 75, 90]
    trading_days: int = 252,
) -> pd.DataFrame:
    """Compute realized volatility percentile distribution across tenors.

    Returns per (symbol, window):
      - window: lookback window in days
      - p10, p25, p50, p75, p90: RV percentiles over full history
      - current: most recent RV value for this window

    Use case: "Is current 21-day RV in the 10th or 90th percentile historically?"
    This tells you whether vol is cheap or expensive at each tenor.

    Input:
      - stock_data: must have underlying_symbol, quote_date, close
    """
```

**Implementation:**
- For each window, compute rolling RV series (annualized close-to-close)
- Compute percentiles over full history of each rolling series
- Return a compact summary table: one row per (symbol, window) with percentile columns + current value
- This is the data behind the "volatility cone" chart

### 1d. IV Term Structure

```python
def iv_term_structure(
    options_data: pd.DataFrame,
    quote_date: str | pd.Timestamp | None = None,  # default: latest date
) -> pd.DataFrame:
    """Extract ATM IV across expirations for a given date.

    Returns per (symbol, expiration):
      - dte: days to expiration
      - atm_iv: ATM implied volatility
      - option_count: number of options used

    Use case: Is near-term vol elevated vs long-term? (backwardation vs contango)
    """
```

**Implementation:**
- Filter to a single quote_date (or latest)
- For each expiration, find the ATM strike (closest to `close`) and average its IV
- Return sorted by DTE

---

## 2. New Signals: `optopsy/signals/iv.py` (extend existing)

Add signals that use the VRP and skew analytics to generate entry/exit dates.

### 2a. VRP Signal

```python
def vrp_above(threshold: float = 0.02, rv_window: int = 21, iv_window: int = 252) -> SignalFunc:
    """True when variance risk premium (IV - RV) exceeds threshold.

    Positive VRP = vol is expensive = favorable for short vol strategies.
    """

def vrp_below(threshold: float = -0.02, rv_window: int = 21, iv_window: int = 252) -> SignalFunc:
    """True when VRP is below threshold.

    Negative VRP = vol is cheap = favorable for long vol strategies.
    """
```

**Implementation:**
- These are `requires_per_strike = True` signals (need options data with IV)
- Internally compute ATM IV and merge with close-to-close RV
- Compare VRP = ATM_IV - RV against threshold
- Follow the `_iv_rank_signal` pattern: compute per (symbol, date), then broadcast back to all rows

### 2b. Skew Signal

```python
def skew_above(threshold: float = 0.05, dte_range: tuple[int, int] = (20, 60)) -> SignalFunc:
    """True when 25-delta put-call skew exceeds threshold.

    High skew = puts expensive relative to calls = mean-reversion opportunity.
    """

def skew_below(threshold: float = 0.02, dte_range: tuple[int, int] = (20, 60)) -> SignalFunc:
    """True when 25-delta skew is below threshold.

    Low/flat skew = puts relatively cheap = potential protection opportunity.
    """
```

### 2c. RV Percentile Signal

```python
def rv_percentile_above(
    percentile: float = 75, window: int = 21, lookback: int = 252
) -> SignalFunc:
    """True when current realized vol is above the Nth percentile of its own history."""

def rv_percentile_below(
    percentile: float = 25, window: int = 21, lookback: int = 252
) -> SignalFunc:
    """True when current realized vol is below the Nth percentile."""
```

---

## 3. UI Tools: `optopsy/ui/tools/_volatility.py`

New tool handlers for the chat agent to call these analytics.

### 3a. Tool: `analyze_vrp`

```python
@_register("analyze_vrp")
def _handle_analyze_vrp(arguments, dataset, signals, datasets, results, _result):
    """Compute variance risk premium for loaded options + stock data."""
```

**Args model** (in `_models.py`):
```python
class AnalyzeVrpArgs(BaseModel):
    rv_windows: list[int] = Field(default=[10, 21, 63], description="RV lookback windows in trading days")
    annualize: bool = Field(default=True)
```

**Behavior:** Calls `variance_risk_premium()` using the current dataset (options) and fetched stock data. Returns a formatted summary table + stores in results for charting.

### 3b. Tool: `analyze_skew`

```python
@_register("analyze_skew")
def _handle_analyze_skew(arguments, dataset, signals, datasets, results, _result):
    """Compute volatility skew metrics."""
```

**Args model:**
```python
class AnalyzeSkewArgs(BaseModel):
    delta_levels: list[float] = Field(default=[0.25, 0.50, 0.75])
    dte_range_min: int = Field(default=20)
    dte_range_max: int = Field(default=60)
    quote_date: str | None = Field(default=None, description="Specific date or latest")
```

### 3c. Tool: `analyze_vol_cone`

```python
@_register("analyze_vol_cone")
def _handle_vol_cone(arguments, dataset, signals, datasets, results, _result):
    """Compute volatility cone from stock price history."""
```

**Args model:**
```python
class AnalyzeVolConeArgs(BaseModel):
    windows: list[int] = Field(default=[10, 21, 42, 63, 126, 252])
    percentiles: list[float] = Field(default=[10, 25, 50, 75, 90])
```

### 3d. Tool: `analyze_iv_term_structure`

```python
@_register("analyze_iv_term_structure")
def _handle_iv_term(arguments, dataset, signals, datasets, results, _result):
    """Extract IV term structure across expirations."""
```

---

## 4. Registration & Exports

### `optopsy/__init__.py`
```python
# Volatility analytics
from .volatility import (
    variance_risk_premium,
    volatility_skew,
    volatility_cone,
    iv_term_structure,
)

# New signals (added to existing iv imports)
from .signals import (
    vrp_above, vrp_below,
    skew_above, skew_below,
    rv_percentile_above, rv_percentile_below,
)
```

### `optopsy/signals/__init__.py`
Add new imports from `iv.py` and add to `__all__`.

### `optopsy/ui/tools/_schemas.py`
```python
# Add to SIGNAL_REGISTRY
"vrp_above": lambda **kw: _signals.vrp_above(
    threshold=kw.get("threshold", 0.02),
    rv_window=kw.get("rv_window", 21),
),
"vrp_below": lambda **kw: _signals.vrp_below(...),
"skew_above": lambda **kw: _signals.skew_above(...),
"skew_below": lambda **kw: _signals.skew_below(...),
"rv_percentile_above": lambda **kw: _signals.rv_percentile_above(...),
"rv_percentile_below": lambda **kw: _signals.rv_percentile_below(...),

# Add to _IV_SIGNALS
_IV_SIGNALS = frozenset({
    "iv_rank_above", "iv_rank_below",
    "vrp_above", "vrp_below",
    "skew_above", "skew_below",
    "rv_percentile_above", "rv_percentile_below",
})

# Add tool descriptions
_TOOL_DESCRIPTIONS["analyze_vrp"] = "Compute variance risk premium (IV minus realized vol) to identify when vol is expensive or cheap for selling/buying."
_TOOL_DESCRIPTIONS["analyze_skew"] = "Analyze volatility skew across strikes — put/call skew, risk reversal, and smile convexity."
_TOOL_DESCRIPTIONS["analyze_vol_cone"] = "Show where current realized vol sits relative to its historical distribution across different lookback windows."
_TOOL_DESCRIPTIONS["analyze_iv_term_structure"] = "Extract ATM implied volatility across expirations to see term structure shape."
```

### `optopsy/ui/tools/_executor.py`
Add import at bottom:
```python
from . import _volatility  # noqa: F401  # register handlers
```

### `optopsy/ui/tools/_models.py`
Add Pydantic models and register in `TOOL_ARG_MODELS` dict.

---

## 5. Tests: `tests/test_volatility.py`

### Test VRP
- Test with synthetic options data (known IV) + synthetic stock data (known returns)
- Verify RV computation: std of log returns * sqrt(252)
- Verify VRP = IV - RV with known values
- Test multiple rv_windows
- Test empty/missing data returns empty DataFrame

### Test Skew
- Create synthetic chain with known IVs at different deltas
- Verify 25d skew = put_iv_25d - call_iv_25d
- Verify risk reversal = call_iv - put_iv
- Verify butterfly = avg(wings) - body
- Test DTE filtering
- Test with missing delta column

### Test Vol Cone
- Create stock data with known return distribution
- Verify percentile calculations match manual numpy percentile
- Verify current value matches last rolling RV
- Test multiple windows

### Test IV Term Structure
- Create options with multiple expirations, known IVs
- Verify sorted by DTE
- Verify ATM selection (closest to close price)

### Test Signals
- `vrp_above/below`: verify boolean series matches threshold comparison
- `skew_above/below`: verify with synthetic skew data
- `rv_percentile_above/below`: verify with known RV history

---

## 6. File Change Summary

| File | Action |
|---|---|
| `optopsy/volatility.py` | **NEW** — core analytics (VRP, skew, cone, term structure) |
| `optopsy/signals/iv.py` | **EDIT** — add VRP, skew, RV percentile signals |
| `optopsy/signals/__init__.py` | **EDIT** — export new signals |
| `optopsy/__init__.py` | **EDIT** — export new analytics + signals |
| `optopsy/ui/tools/_volatility.py` | **NEW** — UI tool handlers |
| `optopsy/ui/tools/_schemas.py` | **EDIT** — register signals + tool descriptions |
| `optopsy/ui/tools/_models.py` | **EDIT** — add Pydantic arg models |
| `optopsy/ui/tools/_executor.py` | **EDIT** — import _volatility module |
| `tests/test_volatility.py` | **NEW** — tests for all analytics + signals |

## 7. Implementation Order

1. `optopsy/volatility.py` — core analytics (no dependencies on other new code)
2. `tests/test_volatility.py` — test analytics in isolation
3. `optopsy/signals/iv.py` — new signals (depends on volatility.py)
4. Signal registration in `__init__.py` files and `_schemas.py`
5. `optopsy/ui/tools/_volatility.py` + models + executor registration
6. Final integration test: run `uv run pytest tests/ -v`
