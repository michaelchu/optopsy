"""Lightweight backtest simulation layer for optopsy strategies.

Sits on top of the existing strategy engine. Calls any strategy function with
``raw=True`` to get individual trades, then simulates executing them
chronologically with capital tracking, position limits, and equity curve
generation.

Example::

    import optopsy as op

    data = op.csv_data("SPX_2018.csv")
    result = op.simulate(data, op.short_puts, max_entry_dte=45, exit_dte=14)
    print(result.summary)
    print(result.trade_log)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import reduce
from typing import Any, Callable, Literal, Union

import numpy as np
import pandas as pd

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SimulationResult:
    """Container for simulation output.

    Attributes:
        trade_log: One row per completed trade with P&L details.
        equity_curve: Indexed by exit date; value is equity after each trade close.
        summary: Flat dict of performance metrics.
    """

    trade_log: pd.DataFrame
    equity_curve: pd.Series
    summary: dict[str, Any]


# ---------------------------------------------------------------------------
# Trade log schema
# ---------------------------------------------------------------------------

_TRADE_LOG_COLUMNS = [
    "trade_id",
    "underlying_symbol",
    "entry_date",
    "exit_date",
    "days_held",
    "expiration",
    "entry_cost",
    "exit_proceeds",
    "quantity",
    "multiplier",
    "dollar_cost",
    "dollar_proceeds",
    "realized_pnl",
    "pct_change",
    "cumulative_pnl",
    "equity",
    "description",
]


# ---------------------------------------------------------------------------
# Column detection helpers
# ---------------------------------------------------------------------------

# Columns that identify a single-leg raw trade
_SINGLE_LEG_COLS = {"entry", "exit", "quote_date_entry"}

# Columns that identify a multi-leg (non-calendar) raw trade
_MULTI_LEG_COST_COLS = {"total_entry_cost", "total_exit_proceeds"}

# Calendar/diagonal strategies have per-leg expirations
_CALENDAR_MARKER = "expiration_leg1"

# Single-leg short strategies — raw output has unsigned option prices (same as
# long), so we negate entry/exit during normalisation to convert to signed cash
# flows: negative entry_cost = credit received, negative exit_proceeds = paid.
_SHORT_SINGLE_LEG = frozenset({"short_calls", "short_puts"})


def _is_single_leg(columns: pd.Index) -> bool:
    return _SINGLE_LEG_COLS.issubset(columns) and "total_entry_cost" not in columns


def _is_calendar(columns: pd.Index) -> bool:
    return _CALENDAR_MARKER in columns


# ---------------------------------------------------------------------------
# Trade normalisation
# ---------------------------------------------------------------------------


def _normalise_trades(
    raw: pd.DataFrame, *, is_short_single: bool = False, exit_dte: int = 0
) -> pd.DataFrame:
    """Map raw strategy output to a uniform schema for the simulation loop.

    Returns a DataFrame with columns:
        entry_date, exit_date, expiration, underlying_symbol,
        entry_cost, exit_proceeds, pct_change, description

    After normalisation, ``entry_cost`` and ``exit_proceeds`` are *signed cash
    flows* using Optopsy's convention: negative values are credits received
    (cash inflow), positive values are debits/amounts paid (cash outflow).
    For multi-leg strategies the raw output already encodes this; for
    single-leg short strategies, the unsigned option prices are negated.

    When *exit_dte* > 0, exit_date is set to ``expiration - exit_dte`` days
    instead of expiration itself.
    """
    cols = raw.columns

    if _is_single_leg(cols):
        df = _normalise_single_leg(raw, negate=is_short_single)
    elif _is_calendar(cols):
        df = _normalise_calendar(raw)
    else:
        # Multi-leg (spreads, butterflies, condors, straddles, strangles)
        df = _normalise_multi_leg(raw)

    if exit_dte > 0:
        df["exit_date"] = df["expiration"] - pd.Timedelta(days=exit_dte)

    return df


def _normalise_single_leg(raw: pd.DataFrame, *, negate: bool = False) -> pd.DataFrame:
    entry_date = _resolve_entry_date(raw)
    expiration = _resolve_expiration(raw)

    # Derive exit date: if dte_entry exists we can compute exit_dte from the
    # strategy params, but the raw output doesn't carry exit_dte directly.
    # For single-leg trades the exit is at expiration (exit_dte=0) or at
    # expiration minus the remaining DTE.  Since we don't have exit quote_date
    # in the raw output, approximate exit_date = expiration.
    exit_date = expiration

    option_type = raw.get("option_type", pd.Series([""] * len(raw), index=raw.index))
    strike = raw.get("strike", pd.Series([np.nan] * len(raw), index=raw.index))
    desc = option_type.astype(str) + " " + strike.astype(str)  # type: ignore[operator]

    # For short single-leg strategies, negate prices to signed cash flows:
    # selling at entry = credit (negative cost), buying back at exit = debit
    # (negative proceeds).  This aligns with multi-leg convention where
    # total_entry_cost < 0 means credit.
    sign = -1 if negate else 1
    entry_cost = raw["entry"] * sign
    exit_proceeds = raw["exit"] * sign

    return pd.DataFrame(
        {
            "entry_date": entry_date,
            "exit_date": exit_date,
            "expiration": expiration,
            "underlying_symbol": raw["underlying_symbol"],
            "entry_cost": entry_cost,
            "exit_proceeds": exit_proceeds,
            "pct_change": raw["pct_change"],
            "description": desc,
        }
    )


def _normalise_multi_leg(raw: pd.DataFrame) -> pd.DataFrame:
    entry_date = _resolve_entry_date(raw)
    expiration = _resolve_expiration(raw)
    exit_date = expiration

    # Build a human-readable description from available strike/type columns
    desc_parts = [
        raw[f"option_type_leg{i}"].astype(str) + " " + raw[f"strike_leg{i}"].astype(str)  # type: ignore[operator]
        for i in range(1, 5)
        if f"option_type_leg{i}" in raw.columns and f"strike_leg{i}" in raw.columns
    ]
    desc = (
        reduce(lambda a, b: a + "/" + b, desc_parts)
        if desc_parts
        else pd.Series(["multi-leg"] * len(raw), index=raw.index)
    )

    return pd.DataFrame(
        {
            "entry_date": entry_date,
            "exit_date": exit_date,
            "expiration": expiration,
            "underlying_symbol": raw["underlying_symbol"],
            "entry_cost": raw["total_entry_cost"],
            "exit_proceeds": raw["total_exit_proceeds"],
            "pct_change": raw["pct_change"],
            "description": desc,
        }
    )


def _normalise_calendar(raw: pd.DataFrame) -> pd.DataFrame:
    entry_date = _resolve_entry_date(raw)

    # Exit date = front expiration (leg1) — the spread is typically closed
    # near front expiration
    exit_date = pd.to_datetime(raw["expiration_leg1"])
    expiration = exit_date

    strike_col = "strike" if "strike" in raw.columns else "strike_leg1"
    strike = raw.get(strike_col, pd.Series([np.nan] * len(raw), index=raw.index))
    option_type = raw.get("option_type", pd.Series([""] * len(raw), index=raw.index))
    desc = "cal " + option_type.astype(str) + " " + strike.astype(str)  # type: ignore[operator]

    return pd.DataFrame(
        {
            "entry_date": entry_date,
            "exit_date": exit_date,
            "expiration": expiration,
            "underlying_symbol": raw["underlying_symbol"],
            "entry_cost": raw["total_entry_cost"],
            "exit_proceeds": raw["total_exit_proceeds"],
            "pct_change": raw["pct_change"],
            "description": desc,
        }
    )


# ---------------------------------------------------------------------------
# Built-in selectors
# ---------------------------------------------------------------------------

# Each selector receives a DataFrame of candidate trades for a single entry
# date (in the raw/pre-normalised schema) and returns a single-row Series.


def _select_one(candidates: pd.DataFrame, idx: Any) -> pd.Series:
    """Return a single row from *candidates* at the given index label."""
    result = candidates.loc[idx]
    assert isinstance(result, pd.Series)
    return result


def _select_nearest(candidates: pd.DataFrame) -> pd.Series:
    """Select the trade closest to ATM (delta closest to 0.50)."""
    for delta_col in ("delta_entry", "delta_entry_leg1"):
        if delta_col in candidates.columns:
            return _select_one(
                candidates, (candidates[delta_col].abs() - 0.50).abs().idxmin()
            )

    # Fallback: use strike - underlying_price distance
    strike_col = "strike" if "strike" in candidates.columns else None
    if strike_col is None and "strike_leg1" in candidates.columns:
        strike_col = "strike_leg1"

    underlying_col: str | None = "underlying_price_entry"
    if underlying_col not in candidates.columns:
        if "underlying_price_entry_leg1" in candidates.columns:
            underlying_col = "underlying_price_entry_leg1"
        else:
            underlying_col = None

    if strike_col is not None and underlying_col is not None:
        distance = (candidates[strike_col] - candidates[underlying_col]).abs()
        return _select_one(candidates, distance.idxmin())

    return candidates.iloc[0]


def _select_highest_premium(candidates: pd.DataFrame) -> pd.Series:
    """Select the trade with the highest credit (most negative entry cost).

    For multi-leg strategies, ``total_entry_cost`` is already signed (negative
    = credit), so ``idxmin`` picks the largest credit.  For single-leg
    strategies, ``entry`` is an unsigned option price, so ``idxmax`` picks the
    highest premium.
    """
    cost_col = _find_cost_col(candidates)
    if cost_col == "entry":
        # Unsigned prices: highest premium = max value
        return _select_one(candidates, candidates[cost_col].idxmax())
    # Signed costs: highest credit = most negative = min value
    return _select_one(candidates, candidates[cost_col].idxmin())


def _select_lowest_premium(candidates: pd.DataFrame) -> pd.Series:
    """Select the trade with the lowest debit (cheapest absolute entry cost)."""
    cost_col = _find_cost_col(candidates)
    return _select_one(candidates, candidates[cost_col].abs().idxmin())


def _select_first(candidates: pd.DataFrame) -> pd.Series:
    """Select the first candidate (deterministic, for testing)."""
    return candidates.iloc[0]


_BUILTIN_SELECTORS: dict[str, Callable[..., pd.Series]] = {
    "nearest": _select_nearest,
    "highest_premium": _select_highest_premium,
    "lowest_premium": _select_lowest_premium,
    "first": _select_first,
}


def _find_cost_col(df: pd.DataFrame) -> str:
    """Find the entry cost column in the dataframe."""
    if "total_entry_cost" in df.columns:
        return "total_entry_cost"
    return "entry"


# ---------------------------------------------------------------------------
# Entry-date column detection
# ---------------------------------------------------------------------------


def _resolve_entry_date(raw: pd.DataFrame) -> pd.Series:
    """Resolve the entry date from raw strategy output.

    Checks for explicit date columns first, then falls back to deriving
    from expiration - DTE.
    """
    for col in ("quote_date_entry", "quote_date_entry_leg1", "quote_date"):
        if col in raw.columns:
            return pd.to_datetime(raw[col])
    return _derive_entry_date(raw)


def _derive_entry_date(raw: pd.DataFrame) -> pd.Series:
    """Derive entry date from expiration and dte_entry when no date column exists."""
    if "expiration" in raw.columns and "dte_entry" in raw.columns:
        exp = pd.to_datetime(raw["expiration"])
        dte = raw["dte_entry"]
    elif "expiration_leg1" in raw.columns and "dte_entry_leg1" in raw.columns:
        exp = pd.to_datetime(raw["expiration_leg1"])
        dte = raw["dte_entry_leg1"]
    else:
        raise ValueError("Cannot derive entry date: no expiration/dte column found")
    return exp - pd.to_timedelta(dte, unit="D")


def _resolve_expiration(raw: pd.DataFrame) -> pd.Series:
    """Resolve the expiration date from raw strategy output."""
    for col in ("expiration", "expiration_leg1"):
        if col in raw.columns:
            return pd.to_datetime(raw[col])
    raise ValueError(f"Cannot determine expiration: columns={list(raw.columns)}")


# ---------------------------------------------------------------------------
# Simulation loop
# ---------------------------------------------------------------------------


def _compute_summary(trade_log: pd.DataFrame, capital: float) -> dict[str, Any]:
    """Compute summary statistics from the trade log.

    Includes both basic trade statistics and risk-adjusted metrics
    (Sharpe, Sortino, VaR, CVaR, Calmar) from the ``metrics`` module.
    """
    from .metrics import (
        calmar_ratio,
        conditional_value_at_risk,
        omega_ratio,
        sharpe_ratio,
        sortino_ratio,
        tail_ratio,
        value_at_risk,
    )
    from .metrics import (
        max_drawdown as _max_drawdown,
    )
    from .metrics import (
        profit_factor as _profit_factor,
    )
    from .metrics import (
        win_rate as _win_rate,
    )

    _empty_risk = {
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "var_95": 0.0,
        "cvar_95": 0.0,
        "calmar_ratio": 0.0,
        "omega_ratio": 0.0,
        "tail_ratio": 0.0,
    }

    if trade_log.empty:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "total_return": 0.0,
            "avg_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_win": 0.0,
            "max_loss": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "avg_days_in_trade": 0.0,
            **_empty_risk,
        }

    pnl = trade_log["realized_pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]

    # Max drawdown from equity curve
    equity = trade_log["equity"]
    max_dd = _max_drawdown(equity)

    # Derive true daily returns from the equity curve for annualised
    # metrics (Sharpe, Sortino, Calmar).  The equity curve is indexed by
    # trade exit dates which are NOT evenly spaced.  Resampling to daily
    # frequency with forward-fill ensures pct_change() produces genuine
    # daily returns suitable for the 252-day annualisation factor.
    _has_dates = "exit_date" in trade_log.columns and "entry_date" in trade_log.columns
    if _has_dates:
        # When multiple trades exit on the same date, use groupby to get
        # the final equity value for each unique exit date. This ensures
        # a unique datetime index required by resample("D").
        equity_daily = trade_log.groupby("exit_date")["equity"].last()
        equity_daily.index = pd.to_datetime(equity_daily.index)
        # Prepend initial capital at the first entry date so the full
        # period is represented (including flat days before first exit).
        first_entry = pd.to_datetime(trade_log["entry_date"].iloc[0])
        if first_entry not in equity_daily.index:
            equity_daily.loc[first_entry] = capital
            equity_daily = equity_daily.sort_index()
        equity_daily = equity_daily.resample("D").ffill()
        daily_returns = equity_daily.pct_change().dropna()
    else:
        # Fallback for minimal trade logs (e.g. unit tests) without date
        # columns — use inter-trade equity changes.
        daily_returns = equity.pct_change().dropna()

    # Per-trade returns are still correct for VaR/CVaR (no annualisation).
    per_trade_returns = trade_log["pct_change"]

    return {
        "total_trades": len(trade_log),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": _win_rate(pnl),
        "total_pnl": float(pnl.sum()),
        "total_return": float(pnl.sum()) / capital if capital > 0 else 0.0,
        "avg_pnl": float(pnl.mean()),
        "avg_win": float(wins.mean()) if len(wins) > 0 else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) > 0 else 0.0,
        "max_win": float(pnl.max()),
        "max_loss": float(pnl.min()),
        "profit_factor": _profit_factor(pnl),
        "max_drawdown": max_dd,
        "avg_days_in_trade": float(trade_log["days_held"].mean()),
        "sharpe_ratio": sharpe_ratio(daily_returns),
        "sortino_ratio": sortino_ratio(daily_returns),
        "var_95": value_at_risk(per_trade_returns, 0.95),
        "cvar_95": conditional_value_at_risk(per_trade_returns, 0.95),
        "calmar_ratio": calmar_ratio(daily_returns),
        "omega_ratio": omega_ratio(daily_returns),
        "tail_ratio": tail_ratio(daily_returns),
    }


def _filter_trades(
    trades: pd.DataFrame,
    max_positions: int,
) -> pd.DataFrame:
    """Filter trades based on position limits and overlap rules.

    Light O(n) scan over trades sorted by entry_date.  For each trade:

    - ``max_positions=1``: keep trade only if its entry_date >= the previous
      kept trade's exit_date (greedy non-overlap).
    - ``max_positions > 1``: track open intervals.  Keep trade if fewer than
      *max_positions* are open **and** no open position shares the same
      expiration.

    Returns the filtered DataFrame of trades that will execute.
    """
    if trades.empty:
        return trades

    n = len(trades)
    entry_dates = trades["entry_date"].values
    exit_dates = trades["exit_date"].values
    expirations = trades["expiration"].values

    keep = np.zeros(n, dtype=bool)

    if max_positions == 1:
        # Fast path: greedy non-overlap
        prev_exit = None
        for i in range(n):
            if prev_exit is None or entry_dates[i] >= prev_exit:
                keep[i] = True
                prev_exit = exit_dates[i]
    else:
        # Track open positions using pre-allocated numpy arrays to avoid
        # repeated Python list creation.  In-place compaction keeps only
        # positions whose exit_date is still in the future.
        _open_exits = np.empty(max_positions, dtype=exit_dates.dtype)
        _open_exps = np.empty(max_positions, dtype=expirations.dtype)
        n_open = 0
        for i in range(n):
            # Compact: remove expired positions in-place
            write = 0
            for j in range(n_open):
                if _open_exits[j] > entry_dates[i]:
                    _open_exits[write] = _open_exits[j]
                    _open_exps[write] = _open_exps[j]
                    write += 1
            n_open = write

            if n_open < max_positions:
                # Check no duplicate expiration
                if expirations[i] not in _open_exps[:n_open]:
                    keep[i] = True
                    _open_exits[n_open] = exit_dates[i]
                    _open_exps[n_open] = expirations[i]
                    n_open += 1

    return trades.loc[keep].reset_index(drop=True)


def _build_trade_log(
    trades: pd.DataFrame,
    capital: float,
    quantity: int,
    multiplier: int,
) -> pd.DataFrame:
    """Compute P&L columns vectorially on filtered trades.

    Returns a DataFrame with :data:`_TRADE_LOG_COLUMNS`.  If equity drops to
    zero or below (ruin), the log is truncated at that trade.
    """
    if trades.empty:
        return pd.DataFrame(columns=_TRADE_LOG_COLUMNS)

    trade_log = pd.DataFrame(
        {
            "trade_id": np.arange(1, len(trades) + 1),
            "underlying_symbol": trades["underlying_symbol"].values,
            "entry_date": trades["entry_date"].values,
            "exit_date": trades["exit_date"].values,
            "expiration": trades["expiration"].values,
            "entry_cost": trades["entry_cost"].values,
            "exit_proceeds": trades["exit_proceeds"].values,
            "quantity": quantity,
            "multiplier": multiplier,
            "pct_change": trades["pct_change"].values,
            "description": trades["description"].values,
        }
    )

    lot_size = quantity * multiplier
    trade_log["dollar_cost"] = trade_log["entry_cost"].abs() * lot_size
    trade_log["dollar_proceeds"] = trade_log["exit_proceeds"] * lot_size
    trade_log["realized_pnl"] = (
        trade_log["exit_proceeds"] - trade_log["entry_cost"]
    ) * lot_size
    trade_log["days_held"] = (
        pd.to_datetime(trade_log["exit_date"]) - pd.to_datetime(trade_log["entry_date"])
    ).dt.days
    trade_log["cumulative_pnl"] = trade_log["realized_pnl"].cumsum()
    trade_log["equity"] = capital + trade_log["cumulative_pnl"]

    # Ruin check: truncate at first trade where equity <= 0
    ruin_mask = trade_log["equity"] <= 0
    if ruin_mask.any():
        ruin_idx = ruin_mask.idxmax()  # first True
        trade_log = trade_log.loc[:ruin_idx]

    return trade_log


def simulate(
    data: pd.DataFrame,
    strategy: Callable[..., pd.DataFrame],
    capital: float = 100_000.0,
    quantity: int = 1,
    max_positions: int = 1,
    multiplier: int = 100,
    selector: Union[
        Literal["nearest", "highest_premium", "lowest_premium", "first"],
        Callable[[pd.DataFrame], pd.Series],
    ] = "nearest",
    **strategy_kwargs: Any,
) -> SimulationResult:
    """Run a chronological simulation of an options strategy.

    Args:
        data: Option chain DataFrame (same format as strategy functions expect).
        strategy: Any optopsy strategy function (e.g. ``op.long_calls``).
        capital: Starting capital in dollars.
        quantity: Number of contracts per trade.
        max_positions: Maximum concurrent open positions.
        multiplier: Contract multiplier (100 for standard equity options).
        selector: How to pick one trade when multiple candidates exist for a
            date.  One of ``"nearest"``, ``"highest_premium"``,
            ``"lowest_premium"``, ``"first"``, or a custom callable.
        **strategy_kwargs: Passed through to the strategy function.

    Returns:
        A :class:`SimulationResult` with trade log, equity curve, and summary.
    """
    # Validate arguments via Pydantic model and use validated values
    from pydantic import ValidationError

    from .checks import _format_validation_error
    from .types import SimulatorParams

    try:
        validated = SimulatorParams(
            capital=capital,
            quantity=quantity,
            max_positions=max_positions,
            multiplier=multiplier,
        )
    except ValidationError as e:
        raise ValueError(_format_validation_error(e)) from e

    capital = validated.capital
    quantity = validated.quantity
    max_positions = validated.max_positions
    multiplier = validated.multiplier

    # Resolve selector
    if isinstance(selector, str):
        if selector not in _BUILTIN_SELECTORS:
            raise ValueError(
                f"Unknown selector '{selector}'. "
                f"Choose from: {list(_BUILTIN_SELECTORS.keys())}"
            )
        select_fn = _BUILTIN_SELECTORS[selector]
    else:
        select_fn = selector

    # Generate raw trades — return empty result for empty input
    if data.empty:
        raw = pd.DataFrame()
    else:
        raw = strategy(data, raw=True, **strategy_kwargs)

    if raw.empty:
        empty_log = pd.DataFrame(columns=_TRADE_LOG_COLUMNS)
        empty_curve = pd.Series(dtype=float, name="equity")
        return SimulationResult(
            trade_log=empty_log,
            equity_curve=empty_curve,
            summary=_compute_summary(empty_log, capital),
        )

    # Select one trade per entry date (on raw data so OTM% columns are
    # available to selectors)
    raw = raw.copy()
    raw["_entry_date"] = _resolve_entry_date(raw)
    group_col = "_entry_date"

    # Group by symbol + entry date so multi-symbol data picks one trade per
    # symbol per date, not one trade across all symbols.
    if "underlying_symbol" in raw.columns:
        group_cols = ["underlying_symbol", group_col]
    else:
        group_cols = [group_col]

    selected_raw = pd.DataFrame(
        [select_fn(group) for _, group in raw.groupby(group_cols)]
    )

    # Detect short single-leg strategies so normalisation can negate prices
    strategy_name = getattr(strategy, "__name__", "")
    is_short_single = strategy_name in _SHORT_SINGLE_LEG

    # Normalise to uniform schema
    exit_dte = int(strategy_kwargs.get("exit_dte", 0))
    trades = _normalise_trades(
        selected_raw, is_short_single=is_short_single, exit_dte=exit_dte
    )
    trades = trades.sort_values("entry_date").reset_index(drop=True)

    # Filter trades by position limits and overlap rules
    filtered = _filter_trades(trades, max_positions)

    # Build trade log with vectorized P&L computation
    trade_log = _build_trade_log(filtered, capital, quantity, multiplier)

    # Build equity curve
    if not trade_log.empty:
        equity_curve = trade_log.set_index("exit_date")["equity"]
        equity_curve.name = "equity"
    else:
        equity_curve = pd.Series(dtype=float, name="equity")

    summary = _compute_summary(trade_log, capital)

    return SimulationResult(
        trade_log=trade_log,
        equity_curve=equity_curve,
        summary=summary,
    )
