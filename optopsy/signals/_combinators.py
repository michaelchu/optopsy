"""Signal combinators, the Signal class, apply_signal, and custom_signal."""

import pandas as pd

from ..timestamps import normalize_dates
from ._helpers import SignalFunc, _groupby_symbol

# ---------------------------------------------------------------------------
# Signal combinators
# ---------------------------------------------------------------------------


def and_signals(*signals: SignalFunc) -> SignalFunc:
    """Combine multiple signals with logical AND.

    All signals must be True for a date to be valid.
    """

    def combined(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(True, index=data.index)
        for sig in signals:
            result = result & sig(data)
        return result

    return combined


def or_signals(*signals: SignalFunc) -> SignalFunc:
    """Combine multiple signals with logical OR.

    At least one signal must be True for a date to be valid.
    """

    def combined(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(False, index=data.index)
        for sig in signals:
            result = result | sig(data)
        return result

    return combined


# ---------------------------------------------------------------------------
# Sustained combinator
# ---------------------------------------------------------------------------


def sustained(signal_func: SignalFunc, days: int = 5) -> SignalFunc:
    """True only when signal_func has been True for at least ``days`` consecutive bars.

    Uses a rolling minimum over the boolean output of the inner signal: the
    window minimum is 1 only when every bar in the window was True.

    Args:
        signal_func: Any SignalFunc to wrap
        days: Minimum consecutive True bars required (default 5)

    Raises:
        ValueError: If days < 1
    """
    if days < 1:
        raise ValueError(f"days must be >= 1, got {days}")

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            raw = signal_func(group)
            return raw.astype(int).rolling(days).min().fillna(0).astype(bool)

        return _groupby_symbol(data, _compute_group)

    return _signal


# ---------------------------------------------------------------------------
# Custom signal from pre-flagged DataFrame
# ---------------------------------------------------------------------------


def custom_signal(df: pd.DataFrame, flag_col: str = "signal") -> SignalFunc:
    """Create a signal function from a DataFrame with a boolean flag column.

    Args:
        df: DataFrame with at least ``underlying_symbol``, ``quote_date``, and
            the boolean flag column.
        flag_col: Name of the column whose truthy values mark valid signal dates.
    """
    required = {"underlying_symbol", "quote_date", flag_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame is missing required columns: {sorted(missing)}")

    flags = df[flag_col].fillna(False).astype(bool)
    valid = df.loc[flags, ["underlying_symbol", "quote_date"]].copy()
    valid["quote_date"] = normalize_dates(valid["quote_date"])
    valid_idx = pd.MultiIndex.from_arrays(
        [valid["underlying_symbol"], valid["quote_date"]]
    )

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        dates = normalize_dates(data["quote_date"])
        lookup = pd.MultiIndex.from_arrays([data["underlying_symbol"], dates])
        return pd.Series(lookup.isin(valid_idx), index=data.index, dtype=bool)

    return _signal


# ---------------------------------------------------------------------------
# Fluent Signal class
# ---------------------------------------------------------------------------


class Signal:
    """Composable wrapper around a SignalFunc with & and | operator support."""

    def __init__(self, func: SignalFunc) -> None:
        self._func = func

    def __call__(self, data: pd.DataFrame) -> "pd.Series[bool]":
        return self._func(data)

    def __and__(self, other: "Signal | SignalFunc") -> "Signal":
        def combined(data: pd.DataFrame) -> "pd.Series[bool]":
            return self(data) & other(data)

        return Signal(combined)

    def __or__(self, other: "Signal | SignalFunc") -> "Signal":
        def combined(data: pd.DataFrame) -> "pd.Series[bool]":
            return self(data) | other(data)

        return Signal(combined)

    def __repr__(self) -> str:
        return f"Signal({self._func!r})"


def signal(func: SignalFunc) -> Signal:
    """Wrap a signal function in a Signal for fluent operator chaining."""
    return Signal(func)


# ---------------------------------------------------------------------------
# apply_signal — public helper to compute valid dates from a signal
# ---------------------------------------------------------------------------


def apply_signal(data: pd.DataFrame, signal_func: SignalFunc) -> pd.DataFrame:
    """Run a signal function on data and return valid (symbol, date) pairs.

    Args:
        data: DataFrame with at least ``underlying_symbol`` and ``quote_date``.
        signal_func: Callable that takes a DataFrame and returns a boolean Series.

    Returns:
        DataFrame with columns ``(underlying_symbol, quote_date)`` for
        dates where the signal is True.
    """
    df = data.copy()
    if "close" not in df.columns and "underlying_price" in df.columns:
        df["close"] = df["underlying_price"]
    elif "underlying_price" not in df.columns and "close" in df.columns:
        df["underlying_price"] = df["close"]
    df["quote_date"] = normalize_dates(df["quote_date"])
    requires_per_strike = getattr(signal_func, "requires_per_strike", False)
    if requires_per_strike:
        df = df.sort_values(["underlying_symbol", "quote_date"]).reset_index(drop=True)
    else:
        df = (
            df.drop_duplicates(["underlying_symbol", "quote_date"])
            .sort_values(["underlying_symbol", "quote_date"])
            .reset_index(drop=True)
        )
    mask = signal_func(df)
    return (
        df.loc[mask, ["underlying_symbol", "quote_date"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
