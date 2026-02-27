"""Basic strategy example — getting started with optopsy.

Demonstrates:
- Loading CSV data with csv_data()
- Running a single-leg strategy with default parameters
- Delta targeting with TargetRange for strike selection
- Viewing aggregated statistics vs. raw individual trades
- Running a multi-leg strategy (iron condor) with per-leg delta targeting

Note: The included sample data is small (~90 rows, 1 month). With a larger
dataset you will see more trades and richer aggregated statistics.
"""

import os

import optopsy as op

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "sample_spx_data.csv")


def load_data():
    """Load the sample SPX option chain data."""
    return op.csv_data(
        DATA_PATH,
        underlying_symbol=0,
        option_type=5,
        expiration=6,
        quote_date=7,
        strike=8,
        bid=10,
        ask=11,
        delta=15,
    )


def main():
    data = load_data()

    # --- 1. Aggregated statistics (default) ---
    # Without TargetRange, optopsy groups results by DTE and delta intervals
    print("=" * 60)
    print("LONG CALLS — Aggregated Statistics")
    print("=" * 60)
    results = op.long_calls(data, max_entry_dte=90, exit_dte=0)
    print(results.round(2).to_string(index=False))

    # --- 2. Delta targeting with TargetRange ---
    # TargetRange filters for strikes near a target delta (absolute value)
    print("\n" + "=" * 60)
    print("LONG CALLS — With Delta Targeting")
    print("=" * 60)
    results = op.long_calls(
        data,
        max_entry_dte=90,
        exit_dte=0,
        leg1_delta=op.TargetRange(target=0.50, min=0.10, max=0.90),
    )
    print(results.round(2).to_string(index=False))

    # --- 3. Raw individual trades ---
    print("\n" + "=" * 60)
    print("LONG CALLS — Raw Trades")
    print("=" * 60)
    raw_trades = op.long_calls(data, raw=True, max_entry_dte=90, exit_dte=0)
    print(raw_trades.head(10).to_string(index=False))

    # --- 4. Multi-leg strategy with per-leg delta targeting ---
    # Iron condor has 4 legs; each can have its own TargetRange.
    # With a larger dataset you would see aggregated statistics here.
    print("\n" + "=" * 60)
    print("IRON CONDOR — Per-Leg Delta Targeting")
    print("=" * 60)
    ic_results = op.iron_condor(
        data,
        max_entry_dte=90,
        exit_dte=0,
        leg1_delta=op.TargetRange(target=0.15, min=0.05, max=0.25),
        leg2_delta=op.TargetRange(target=0.30, min=0.15, max=0.45),
        leg3_delta=op.TargetRange(target=0.30, min=0.15, max=0.45),
        leg4_delta=op.TargetRange(target=0.15, min=0.05, max=0.25),
    )
    if ic_results.empty:
        print("No iron condor trades found (sample data is too small).")
        print("With a larger dataset, this would show aggregated statistics.")
    else:
        print(ic_results.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
