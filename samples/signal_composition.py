"""Signal composition example — filtering entries with technical signals.

Demonstrates:
- Combining signals with and_signals / or_signals
- Using sustained() for multi-day confirmation
- apply_signal() to produce entry_dates for a strategy
- IV rank signal for premium-selling regimes
- custom_signal() from a user-created DataFrame

Note: Many signals (RSI, Bollinger, etc.) require OHLCV stock price data.
      When option chain data lacks a 'close' column, pass stock_data= to
      apply_signal().  This example uses the option chain's underlying_last
      column mapped via csv_data(underlying_price=1) as a proxy.
"""

import os

import pandas as pd

import optopsy as op

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "sample_spx_data.csv")


def load_data():
    """Load data with implied_volatility for IV rank signals."""
    return op.csv_data(
        DATA_PATH,
        underlying_symbol=0,
        underlying_price=1,
        option_type=5,
        expiration=6,
        quote_date=7,
        strike=8,
        bid=10,
        ask=11,
        delta=15,
        implied_volatility=14,
    )


def main():
    data = load_data()

    # --- 1. Single signal: only enter on Thursdays ---
    print("=" * 60)
    print("ENTRY SIGNAL — Thursdays Only")
    print("=" * 60)
    thursday_dates = op.apply_signal(data, op.day_of_week(3))
    print(f"Entry dates found: {len(thursday_dates)}")

    results = op.long_puts(
        data,
        max_entry_dte=90,
        exit_dte=0,
        entry_dates=thursday_dates,
    )
    if results.empty:
        print("No trades matched (expected with small sample data).")
    else:
        print(results.round(2).to_string(index=False))

    # --- 2. Combined signals: RSI oversold + Bollinger below lower band ---
    print("\n" + "=" * 60)
    print("COMBINED SIGNAL — RSI Oversold + Bollinger Lower")
    print("=" * 60)
    combined = op.and_signals(
        op.rsi_below(period=14, threshold=30),
        op.bb_below_lower(length=20, std=2.0),
    )
    entry_dates = op.apply_signal(data, combined)
    print(f"Entry dates matching both conditions: {len(entry_dates)}")

    if len(entry_dates) > 0:
        results = op.long_calls(
            data,
            max_entry_dte=60,
            exit_dte=14,
            entry_dates=entry_dates,
        )
        print(results.round(2).to_string(index=False))
    else:
        print("No matching dates in sample data (expected with short dataset).")

    # --- 3. Sustained signal: RSI above 70 for 3 consecutive days ---
    print("\n" + "=" * 60)
    print("SUSTAINED SIGNAL — RSI Overbought for 3 Days")
    print("=" * 60)
    overbought_3d = op.sustained(op.rsi_above(period=14, threshold=70), days=3)
    entry_dates = op.apply_signal(data, overbought_3d)
    print(f"Sustained overbought dates: {len(entry_dates)}")

    # --- 4. IV rank signal: sell premium when IV is high ---
    print("\n" + "=" * 60)
    print("IV RANK SIGNAL — Sell Premium in High IV")
    print("=" * 60)
    high_iv = op.iv_rank_above(threshold=0.5, window=252)
    iv_dates = op.apply_signal(data, high_iv)
    print(f"High IV rank dates: {len(iv_dates)}")

    if len(iv_dates) > 0:
        results = op.short_puts(
            data,
            max_entry_dte=45,
            exit_dte=14,
            entry_dates=iv_dates,
        )
        print(results.round(2).to_string(index=False))
    else:
        print("No high-IV dates found (needs longer history for 252-day window).")

    # --- 5. Custom signal from user-created DataFrame ---
    print("\n" + "=" * 60)
    print("CUSTOM SIGNAL — User-Defined Entry Dates")
    print("=" * 60)
    # Build a custom signal DataFrame marking specific dates
    custom_df = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"] * 3,
            "quote_date": pd.to_datetime(["2015-10-01", "2015-10-15", "2015-10-29"]),
            "signal": [True, True, True],
        }
    )
    custom_dates = op.apply_signal(data, op.custom_signal(custom_df))
    print(f"Custom entry dates: {len(custom_dates)}")

    results = op.long_calls(
        data,
        max_entry_dte=90,
        exit_dte=0,
        entry_dates=custom_dates,
    )
    if results.empty:
        print("No trades matched (expected with small sample data).")
    else:
        print(results.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
