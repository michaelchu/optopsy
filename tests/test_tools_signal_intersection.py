"""Tests for _intersect_with_options_dates and _empty_signal_suggestion."""

import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from optopsy.ui.tools import (
    _empty_signal_suggestion,
    _intersect_with_options_dates,
    execute_tool,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal_dates(symbol: str, dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "underlying_symbol": symbol,
            "quote_date": pd.to_datetime(dates),
        }
    )


def _make_options(symbol: str, dates: list[str]) -> pd.DataFrame:
    """Minimal options DataFrame with just the columns needed for intersection."""
    return pd.DataFrame(
        {
            "underlying_symbol": symbol,
            "quote_date": pd.to_datetime(dates),
            "strike": 100.0,
        }
    )


# ---------------------------------------------------------------------------
# _intersect_with_options_dates
# ---------------------------------------------------------------------------


def test_intersect_keeps_matching_dates():
    signals = _make_signal_dates("SPY", ["2024-12-19", "2025-12-16", "2025-12-17"])
    options = _make_options("SPY", ["2025-12-16", "2025-12-17", "2026-01-15"])
    result = _intersect_with_options_dates(signals, options)
    assert sorted(result["quote_date"].dt.date.tolist()) == [
        datetime.date(2025, 12, 16),
        datetime.date(2025, 12, 17),
    ]


def test_intersect_returns_empty_when_no_overlap():
    signals = _make_signal_dates("SPY", ["2024-01-01", "2024-06-01"])
    options = _make_options("SPY", ["2025-12-16", "2026-01-15"])
    result = _intersect_with_options_dates(signals, options)
    assert result.empty


def test_intersect_empty_signal_dates_returns_empty():
    empty = pd.DataFrame(columns=["underlying_symbol", "quote_date"])
    options = _make_options("SPY", ["2025-12-16"])
    result = _intersect_with_options_dates(empty, options)
    assert result.empty


def test_intersect_empty_options_returns_signal_unchanged():
    signals = _make_signal_dates("SPY", ["2025-12-16"])
    empty_opts = pd.DataFrame(columns=["underlying_symbol", "quote_date", "strike"])
    result = _intersect_with_options_dates(signals, empty_opts)
    # When options is empty, signal_dates is returned as-is
    assert len(result) == 1


def test_intersect_normalises_timestamps():
    """Time components should not prevent a match."""
    signals = pd.DataFrame(
        {
            "underlying_symbol": ["SPY"],
            "quote_date": pd.to_datetime(["2025-12-16 20:59:59"]),
        }
    )
    options = pd.DataFrame(
        {
            "underlying_symbol": ["SPY"],
            "quote_date": pd.to_datetime(["2025-12-16 00:00:00"]),
            "strike": [580.0],
        }
    )
    result = _intersect_with_options_dates(signals, options)
    assert len(result) == 1


def test_intersect_scoped_to_symbol():
    """Dates should only match for the same underlying symbol."""
    signals = _make_signal_dates("SPY", ["2025-12-16"])
    options = _make_options("QQQ", ["2025-12-16"])
    result = _intersect_with_options_dates(signals, options)
    assert result.empty


# ---------------------------------------------------------------------------
# _empty_signal_suggestion
# ---------------------------------------------------------------------------

OPT_MIN = datetime.date(2025, 12, 16)
OPT_MAX = datetime.date(2026, 1, 15)


def test_suggestion_never_fired():
    empty = pd.DataFrame(columns=["underlying_symbol", "quote_date"])
    msg = _empty_signal_suggestion(empty, OPT_MIN, OPT_MAX)
    assert "never fired" in msg.lower()
    assert "relax" in msg.lower()


def test_suggestion_fired_before_window():
    raw = _make_signal_dates("SPY", ["2024-12-19", "2024-12-20"])
    msg = _empty_signal_suggestion(raw, OPT_MIN, OPT_MAX)
    assert "2024-12-20" in msg
    assert "before" in msg.lower()
    # Should suggest a range bracketing that date
    assert "2024-11-20" in msg  # last_before - 30 days
    assert "2025-01-19" in msg  # last_before + 30 days


def test_suggestion_fired_after_window():
    raw = _make_signal_dates("SPY", ["2026-02-01", "2026-03-01"])
    msg = _empty_signal_suggestion(raw, OPT_MIN, OPT_MAX)
    assert "2026-02-01" in msg
    assert "after" in msg.lower()
    assert "2026-01-02" in msg  # first_after - 30 days
    assert "2026-03-03" in msg  # first_after + 30 days


def test_suggestion_fired_both_sides():
    raw = _make_signal_dates("SPY", ["2024-12-19", "2026-03-01"])
    msg = _empty_signal_suggestion(raw, OPT_MIN, OPT_MAX)
    assert "before" in msg.lower()
    assert "after" in msg.lower()


def test_suggestion_data_gap_within_window():
    """Signal fired inside the options window but dates weren't in the dataset."""
    # Fired dates are within [OPT_MIN, OPT_MAX] but not in the options data —
    # this triggers the data-gap branch.
    raw = _make_signal_dates("SPY", ["2025-12-25"])  # Christmas — likely a market holiday
    msg = _empty_signal_suggestion(raw, OPT_MIN, OPT_MAX)
    assert "data gap" in msg.lower() or "not present" in msg.lower()


# ---------------------------------------------------------------------------
# Integration: run_strategy entry signal no-overlap → suggestion message
# ---------------------------------------------------------------------------


@pytest.fixture
def options_dec_2025():
    """Minimal options dataset covering Dec 2025 – Jan 2026."""
    dates = pd.date_range("2025-12-16", "2026-01-15", freq="B")
    exp = pd.Timestamp("2026-01-16")
    rows = []
    for d in dates:
        for strike in [580.0, 590.0]:
            rows.append(
                {
                    "underlying_symbol": "SPY",
                    "underlying_price": 585.0,
                    "option_type": "call",
                    "expiration": exp,
                    "quote_date": d,
                    "strike": strike,
                    "bid": 5.0,
                    "ask": 5.1,
                }
            )
    return pd.DataFrame(rows)


def test_entry_signal_no_overlap_gives_suggestion(options_dec_2025):
    """When RSI fires only in the yfinance warmup period, the error message
    should name the date it last fired and suggest a concrete fetch range."""
    # Fake yfinance data: RSI is below 35 only in early 2025 (before the options window)
    warmup_dates = pd.date_range("2024-12-16", "2025-12-15", freq="B")
    fake_stock = pd.DataFrame(
        {
            "underlying_symbol": "SPY",
            "quote_date": warmup_dates,
            # Price drops sharply at the end of 2024 to trigger RSI < 35
            "underlying_price": [500.0] * (len(warmup_dates) - 5)
            + [300.0] * 5,  # last 5 bars deeply oversold
            "open": 500.0,
            "high": 500.0,
            "low": 500.0,
            "close": [500.0] * (len(warmup_dates) - 5) + [300.0] * 5,
            "volume": 1_000_000,
        }
    )

    with patch(
        "optopsy.ui.tools._fetch_stock_data_for_signals",
        return_value=fake_stock,
    ):
        result = execute_tool(
            "run_strategy",
            {
                "strategy_name": "long_calls",
                "entry_signal": "rsi_below",
                "entry_signal_params": {"threshold": 35},
                "raw": True,
            },
            options_dec_2025,
        )

    summary = result.llm_summary.lower()
    assert "no dates overlapping" in summary or "produced no dates" in summary
    # Should include a concrete date suggestion — either "before" or "never fired"
    assert any(
        keyword in summary
        for keyword in ("before", "never fired", "fetch options from", "data gap")
    )


def test_exit_signal_no_overlap_gives_suggestion(options_dec_2025):
    """Exit signal with no overlap should also return a suggestion, not silence."""
    warmup_dates = pd.date_range("2024-12-16", "2025-12-15", freq="B")
    fake_stock = pd.DataFrame(
        {
            "underlying_symbol": "SPY",
            "quote_date": warmup_dates,
            "underlying_price": [500.0] * len(warmup_dates),
            "open": 500.0,
            "high": 600.0,
            "low": 500.0,
            "close": [500.0] * len(warmup_dates),
            "volume": 1_000_000,
        }
    )

    with patch(
        "optopsy.ui.tools._fetch_stock_data_for_signals",
        return_value=fake_stock,
    ):
        result = execute_tool(
            "run_strategy",
            {
                "strategy_name": "long_calls",
                "exit_signal": "rsi_above",
                "exit_signal_params": {"threshold": 70},
                "raw": True,
            },
            options_dec_2025,
        )

    summary = result.llm_summary.lower()
    # Should not silently return strategy results with an empty exit filter;
    # should return an actionable error about the exit signal
    assert "exit signal" in summary


def test_build_signal_no_overlap_gives_suggestion(options_dec_2025):
    """build_signal with 0 overlapping dates should include a suggestion."""
    warmup_dates = pd.date_range("2024-12-16", "2025-12-15", freq="B")
    fake_stock = pd.DataFrame(
        {
            "underlying_symbol": "SPY",
            "quote_date": warmup_dates,
            "underlying_price": [500.0] * (len(warmup_dates) - 5) + [300.0] * 5,
            "open": 500.0,
            "high": 500.0,
            "low": 500.0,
            "close": [500.0] * (len(warmup_dates) - 5) + [300.0] * 5,
            "volume": 1_000_000,
        }
    )

    with patch(
        "optopsy.ui.tools._fetch_stock_data_for_signals",
        return_value=fake_stock,
    ):
        result = execute_tool(
            "build_signal",
            {
                "slot": "entry",
                "signals": [{"name": "rsi_below", "params": {"threshold": 35}}],
            },
            options_dec_2025,
        )

    display = result.user_display.lower()
    assert "warning" in display
    assert any(
        keyword in display
        for keyword in ("before", "never fired", "fetch options from", "data gap")
    )
