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
    equity_curve: pd.Series  # type: ignore[type-arg]
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
    raw: pd.DataFrame, *, is_short_single: bool = False
) -> pd.DataFrame:
    """Map raw strategy output to a uniform schema for the simulation loop.

    Returns a DataFrame with columns:
        entry_date, exit_date, expiration, underlying_symbol,
        entry_cost, exit_proceeds, pct_change, description

    After normalisation, ``entry_cost`` and ``exit_proceeds`` are *signed cash
    flows*: negative means cash outflow (paid), positive means cash inflow
    (received).  For multi-leg strategies the raw output already encodes this.
    For single-leg short strategies, the unsigned option prices are negated.
    """
    cols = raw.columns

    if _is_single_leg(cols):
        return _normalise_single_leg(raw, negate=is_short_single)
    if _is_calendar(cols):
        return _normalise_calendar(raw)
    # Multi-leg (spreads, butterflies, condors, straddles, strangles)
    return _normalise_multi_leg(raw)


def _normalise_single_leg(raw: pd.DataFrame, *, negate: bool = False) -> pd.DataFrame:
    entry_date = pd.to_datetime(raw["quote_date_entry"])
    expiration = pd.to_datetime(raw["expiration"])

    # Derive exit date: if dte_entry exists we can compute exit_dte from the
    # strategy params, but the raw output doesn't carry exit_dte directly.
    # For single-leg trades the exit is at expiration (exit_dte=0) or at
    # expiration minus the remaining DTE.  Since we don't have exit quote_date
    # in the raw output, approximate exit_date = expiration.
    exit_date = expiration

    option_type = raw.get("option_type", pd.Series([""] * len(raw), index=raw.index))
    strike = raw.get("strike", pd.Series([np.nan] * len(raw), index=raw.index))
    desc = option_type.astype(str) + " " + strike.astype(str)

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
    # Find quote_date_entry — may be named differently after multi-leg merge
    if "quote_date_entry" in raw.columns:
        entry_date = pd.to_datetime(raw["quote_date_entry"])
    elif "quote_date_entry_leg1" in raw.columns:
        entry_date = pd.to_datetime(raw["quote_date_entry_leg1"])
    elif "dte_entry" in raw.columns and "expiration" in raw.columns:
        entry_date = _derive_entry_date(raw)
    else:
        raise ValueError(
            "Cannot determine entry date for multi-leg trade: "
            f"columns={list(raw.columns)}"
        )

    if "expiration" in raw.columns:
        expiration = pd.to_datetime(raw["expiration"])
    elif "expiration_leg1" in raw.columns:
        expiration = pd.to_datetime(raw["expiration_leg1"])
    else:
        raise ValueError(
            "Cannot determine expiration for multi-leg trade: "
            f"columns={list(raw.columns)}"
        )
    exit_date = expiration

    # Build a human-readable description from available strike/type columns
    desc_parts = []
    for i in range(1, 5):
        type_col = f"option_type_leg{i}"
        strike_col = f"strike_leg{i}"
        if type_col in raw.columns and strike_col in raw.columns:
            desc_parts.append(
                raw[type_col].astype(str) + " " + raw[strike_col].astype(str)
            )
    if desc_parts:
        desc = desc_parts[0]
        for part in desc_parts[1:]:
            desc = desc + "/" + part
    else:
        desc = pd.Series(["multi-leg"] * len(raw), index=raw.index)

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
    # Calendar spreads: entry date from quote_date or derived from
    # expiration_leg1 - dte_entry_leg1
    if "quote_date" in raw.columns:
        entry_date = pd.to_datetime(raw["quote_date"])
    elif "quote_date_entry" in raw.columns:
        entry_date = pd.to_datetime(raw["quote_date_entry"])
    elif "dte_entry_leg1" in raw.columns and "expiration_leg1" in raw.columns:
        exp = pd.to_datetime(raw["expiration_leg1"])
        entry_date = exp - pd.to_timedelta(raw["dte_entry_leg1"], unit="D")
    else:
        raise ValueError(
            "Cannot determine entry date for calendar trade: "
            f"columns={list(raw.columns)}"
        )

    # Exit date = front expiration (leg1) — the spread is typically closed
    # near front expiration
    exit_date = pd.to_datetime(raw["expiration_leg1"])
    expiration = exit_date

    strike_col = "strike" if "strike" in raw.columns else "strike_leg1"
    strike = raw.get(strike_col, pd.Series([np.nan] * len(raw), index=raw.index))
    option_type = raw.get("option_type", pd.Series([""] * len(raw), index=raw.index))
    desc = "cal " + option_type.astype(str) + " " + strike.astype(str)

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


def _select_nearest(candidates: pd.DataFrame) -> pd.Series:  # type: ignore[type-arg]
    """Select the trade closest to ATM (lowest absolute OTM%)."""
    otm_col = _find_otm_col(candidates)
    if otm_col is None:
        return candidates.iloc[0]
    idx = candidates[otm_col].abs().idxmin()
    result = candidates.loc[idx]
    assert isinstance(result, pd.Series)
    return result


def _select_highest_premium(candidates: pd.DataFrame) -> pd.Series:  # type: ignore[type-arg]
    """Select the trade with the highest credit (most negative entry cost)."""
    cost_col = _find_cost_col(candidates)
    idx = candidates[cost_col].idxmin()
    result = candidates.loc[idx]
    assert isinstance(result, pd.Series)
    return result


def _select_lowest_premium(candidates: pd.DataFrame) -> pd.Series:  # type: ignore[type-arg]
    """Select the trade with the lowest debit (cheapest absolute entry cost)."""
    cost_col = _find_cost_col(candidates)
    idx = candidates[cost_col].abs().idxmin()
    result = candidates.loc[idx]
    assert isinstance(result, pd.Series)
    return result


def _select_first(candidates: pd.DataFrame) -> pd.Series:  # type: ignore[type-arg]
    """Select the first candidate (deterministic, for testing)."""
    return candidates.iloc[0]


_BUILTIN_SELECTORS: dict[str, Callable[..., pd.Series]] = {  # type: ignore[type-arg]
    "nearest": _select_nearest,
    "highest_premium": _select_highest_premium,
    "lowest_premium": _select_lowest_premium,
    "first": _select_first,
}


def _find_otm_col(df: pd.DataFrame) -> str | None:
    """Find the OTM percentage column in the dataframe."""
    for col in ("otm_pct_entry", "otm_pct_entry_leg1", "otm_pct_leg1"):
        if col in df.columns:
            return col
    return None


def _find_cost_col(df: pd.DataFrame) -> str:
    """Find the entry cost column in the dataframe."""
    if "total_entry_cost" in df.columns:
        return "total_entry_cost"
    return "entry"


# ---------------------------------------------------------------------------
# Entry-date column detection
# ---------------------------------------------------------------------------


def _find_entry_date_col(df: pd.DataFrame) -> str | None:
    """Find the column representing the entry/quote date in raw output.

    Returns the column name if found, or None if the entry date must be
    derived from ``expiration`` and ``dte_entry``.
    """
    for col in ("quote_date_entry", "quote_date_entry_leg1", "quote_date"):
        if col in df.columns:
            return col
    return None


def _derive_entry_date(df: pd.DataFrame) -> pd.Series:  # type: ignore[type-arg]
    """Derive entry date from expiration and dte_entry when no date column exists."""
    if "expiration" in df.columns and "dte_entry" in df.columns:
        exp = pd.to_datetime(df["expiration"])
        dte = df["dte_entry"]
    elif "expiration_leg1" in df.columns and "dte_entry_leg1" in df.columns:
        exp = pd.to_datetime(df["expiration_leg1"])
        dte = df["dte_entry_leg1"]
    else:
        raise ValueError("Cannot derive entry date: no expiration/dte column found")
    return exp - pd.to_timedelta(dte, unit="D")


# ---------------------------------------------------------------------------
# Simulation loop
# ---------------------------------------------------------------------------


def _compute_summary(trade_log: pd.DataFrame, capital: float) -> dict[str, Any]:
    """Compute summary statistics from the trade log."""
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
        }

    pnl = trade_log["realized_pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    total_wins = float(wins.sum()) if len(wins) > 0 else 0.0
    total_losses = float(losses.sum()) if len(losses) > 0 else 0.0

    # Max drawdown from equity curve
    equity = trade_log["equity"]
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_dd = float(drawdown.min()) if len(drawdown) > 0 else 0.0

    return {
        "total_trades": len(trade_log),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": len(wins) / len(trade_log) if len(trade_log) > 0 else 0.0,
        "total_pnl": float(pnl.sum()),
        "total_return": float(pnl.sum()) / capital if capital > 0 else 0.0,
        "avg_pnl": float(pnl.mean()),
        "avg_win": float(wins.mean()) if len(wins) > 0 else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) > 0 else 0.0,
        "max_win": float(pnl.max()),
        "max_loss": float(pnl.min()),
        "profit_factor": (
            abs(total_wins / total_losses) if total_losses != 0 else float("inf")
        ),
        "max_drawdown": max_dd,
        "avg_days_in_trade": float(trade_log["days_held"].mean()),
    }


def simulate(
    data: pd.DataFrame,
    strategy: Callable[..., pd.DataFrame],
    capital: float = 100_000.0,
    quantity: int = 1,
    max_positions: int = 1,
    multiplier: int = 100,
    selector: Union[
        Literal["nearest", "highest_premium", "lowest_premium", "first"],
        Callable[[pd.DataFrame], pd.Series],  # type: ignore[type-arg]
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

    # Generate raw trades
    try:
        raw = strategy(data, raw=True, **strategy_kwargs)
    except Exception:
        _log.debug(
            "Strategy raised an exception, returning empty result", exc_info=True
        )
        raw = pd.DataFrame()

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
    entry_date_col = _find_entry_date_col(raw)
    raw = raw.copy()
    if entry_date_col is not None:
        raw[entry_date_col] = pd.to_datetime(raw[entry_date_col])
        group_col = entry_date_col
    else:
        # Derive entry date from expiration - dte_entry
        raw["_entry_date"] = _derive_entry_date(raw)
        group_col = "_entry_date"

    selected_rows = []
    for _, group in raw.groupby(group_col):
        row = select_fn(group)
        selected_rows.append(row)

    selected_raw = pd.DataFrame(selected_rows)

    # Detect short single-leg strategies so normalisation can negate prices
    strategy_name = getattr(strategy, "__name__", "")
    is_short_single = strategy_name in _SHORT_SINGLE_LEG

    # Normalise to uniform schema
    trades = _normalise_trades(selected_raw, is_short_single=is_short_single)
    trades = trades.sort_values("entry_date").reset_index(drop=True)

    # Simulation loop
    cash = capital
    cumulative_pnl = 0.0
    open_positions: list[dict[str, Any]] = []
    completed_trades: list[dict[str, Any]] = []
    trade_id = 0

    # Build a set of all dates we need to process
    all_dates = sorted(
        set(trades["entry_date"].tolist() + trades["exit_date"].tolist())
    )

    # Index trades by entry date for quick lookup (first occurrence per date)
    _first_idx = trades.drop_duplicates("entry_date", keep="first").index
    entry_date_map: dict[Any, int] = {
        trades.at[i, "entry_date"]: i
        for i in _first_idx  # type: ignore[misc]
    }

    def _close_pos(pos: dict[str, Any]) -> dict[str, Any]:
        """Build a completed-trade dict and compute realized P&L.

        After normalisation, entry_cost and exit_proceeds are signed cash
        flows.  P&L is always ``(exit_proceeds - entry_cost) * qty * mult``.
        """
        qty = pos["quantity"]
        mult = pos["multiplier"]
        dollar_cost = abs(pos["entry_cost"]) * qty * mult
        realized = (pos["exit_proceeds"] - pos["entry_cost"]) * qty * mult
        return {
            "dollar_cost": dollar_cost,
            "dollar_proceeds": pos["exit_proceeds"] * qty * mult,
            "realized_pnl": realized,
            "days_held": (pos["exit_date"] - pos["entry_date"]).days,
        }

    for current_date in all_dates:
        # Close positions whose exit_date has arrived
        still_open = []
        for pos in open_positions:
            if pos["exit_date"] <= current_date:
                closed = _close_pos(pos)
                cumulative_pnl += closed["realized_pnl"]
                cash += closed["dollar_cost"] + closed["realized_pnl"]

                completed_trades.append(
                    {
                        **{
                            k: pos[k]
                            for k in pos
                            if k != "quantity" and k != "multiplier"
                        },
                        "quantity": pos["quantity"],
                        "multiplier": pos["multiplier"],
                        **closed,
                        "pct_change": pos["pct_change"],
                        "cumulative_pnl": cumulative_pnl,
                        "equity": capital + cumulative_pnl,
                    }
                )
            else:
                still_open.append(pos)
        open_positions = still_open

        # Try to open a new position if there's a trade for this date
        if current_date in entry_date_map and len(open_positions) < max_positions:
            idx = entry_date_map[current_date]
            trade = trades.loc[idx]

            # Check no duplicate expirations when max_positions > 1
            if max_positions > 1:
                open_expirations = {p["expiration"] for p in open_positions}
                if trade["expiration"] in open_expirations:
                    continue

            dollar_cost = abs(trade["entry_cost"]) * quantity * multiplier

            if dollar_cost <= cash:
                cash -= dollar_cost
                trade_id += 1
                open_positions.append(
                    {
                        "trade_id": trade_id,
                        "underlying_symbol": trade["underlying_symbol"],
                        "entry_date": trade["entry_date"],
                        "exit_date": trade["exit_date"],
                        "expiration": trade["expiration"],
                        "entry_cost": trade["entry_cost"],
                        "exit_proceeds": trade["exit_proceeds"],
                        "pct_change": trade["pct_change"],
                        "quantity": quantity,
                        "multiplier": multiplier,
                        "description": trade["description"],
                    }
                )

    # Close any remaining open positions at end
    for pos in open_positions:
        closed = _close_pos(pos)
        cumulative_pnl += closed["realized_pnl"]
        cash += closed["dollar_cost"] + closed["realized_pnl"]

        completed_trades.append(
            {
                **{k: pos[k] for k in pos if k != "quantity" and k != "multiplier"},
                "quantity": pos["quantity"],
                "multiplier": pos["multiplier"],
                **closed,
                "pct_change": pos["pct_change"],
                "cumulative_pnl": cumulative_pnl,
                "equity": capital + cumulative_pnl,
            }
        )

    # Build trade log DataFrame
    trade_log = pd.DataFrame(completed_trades)
    if trade_log.empty:
        trade_log = pd.DataFrame(columns=_TRADE_LOG_COLUMNS)

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
