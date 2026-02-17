"""
Benchmark: old 4-column merge vs new arithmetic contract_id merge.

Generates synthetic option chain data at various scales and measures the
wall-clock time of the entry/exit merge step in isolation.
"""

import time
import numpy as np
import pandas as pd


def generate_option_data(
    n_expirations: int = 12,
    n_strikes: int = 50,
    n_quote_days: int = 30,
    symbol: str = "SPX",
) -> pd.DataFrame:
    base_date = pd.Timestamp("2023-01-01")
    expirations = [base_date + pd.Timedelta(days=30 * (i + 1)) for i in range(n_expirations)]
    strikes = np.linspace(4000, 5000, n_strikes)
    option_types = ["call", "put"]

    rows = []
    for exp in expirations:
        quote_dates_for_exp = [base_date + pd.Timedelta(days=d) for d in range(n_quote_days)]
        quote_dates_for_exp.append(exp)
        for quote_date in quote_dates_for_exp:
            if quote_date > exp:
                continue
            dte = (exp - quote_date).days
            underlying_price = 4500 + np.random.randn() * 20
            for ot in option_types:
                for strike in strikes:
                    mid = max(0.05, abs(underlying_price - strike) * 0.3 + dte * 0.1 + np.random.rand())
                    spread = mid * 0.02
                    rows.append([
                        symbol, round(underlying_price, 2), ot, exp, quote_date,
                        round(strike, 2), round(max(0.01, mid - spread), 2), round(mid + spread, 2),
                    ])

    return pd.DataFrame(
        rows,
        columns=["underlying_symbol", "underlying_price", "option_type",
                 "expiration", "quote_date", "strike", "bid", "ask"],
    )


def prepare_data(data, exit_dte=0):
    data = data.copy()
    data["dte"] = (data["expiration"] - data["quote_date"]).dt.days
    entries = data[(data["dte"] > exit_dte) & ((data["bid"] + data["ask"]) / 2 > 0.05)].copy()
    exits = data[data["dte"] == exit_dte].copy()
    return entries, exits


def add_contract_id(entries, exits):
    for df in (entries, exits):
        df["contract_id"] = (
            df["underlying_symbol"].astype("category").cat.codes.astype(np.int64) * 1_000_000_000_000
            + df["option_type"].astype("category").cat.codes.astype(np.int64) * 100_000_000_000
            + (df["expiration"] - df["expiration"].min()).dt.days.astype(np.int64) * 10_000_000
            + (df["strike"] * 100).astype(np.int64)
        )
    return entries, exits


MERGE_COLS = ["underlying_symbol", "option_type", "expiration", "strike"]


def merge_old(entries, exits):
    """Original: 4-column merge."""
    return entries.merge(right=exits, on=MERGE_COLS, suffixes=("_entry", "_exit"))


def merge_new(entries, exits):
    """Optimized: single contract_id merge."""
    return entries.merge(right=exits, on="contract_id", suffixes=("_entry", "_exit"))


def bench(fn, entries, exits, n_runs=7):
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        result = fn(entries, exits)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    median = sorted(times)[len(times) // 2]
    return median, len(result)


def main():
    configs = [
        {"n_expirations": 4,   "n_strikes": 20,  "n_quote_days": 10, "label": "Small"},
        {"n_expirations": 12,  "n_strikes": 50,  "n_quote_days": 30, "label": "Medium"},
        {"n_expirations": 24,  "n_strikes": 100, "n_quote_days": 30, "label": "Large"},
        {"n_expirations": 24,  "n_strikes": 200, "n_quote_days": 60, "label": "XL"},
    ]

    print(f"{'Config':<10} {'Rows':>10} {'Old (ms)':>10} {'New (ms)':>10} {'Speedup':>10} {'Result rows':>12}")
    print("-" * 66)

    for cfg in configs:
        label = cfg.pop("label")
        np.random.seed(42)
        data = generate_option_data(**cfg)
        entries, exits = prepare_data(data, exit_dte=0)
        entries_keyed, exits_keyed = add_contract_id(entries.copy(), exits.copy())

        # Warmup
        merge_old(entries, exits)
        merge_new(entries_keyed, exits_keyed)

        old_ms, old_rows = bench(merge_old, entries, exits)
        new_ms, new_rows = bench(merge_new, entries_keyed, exits_keyed)
        speedup = old_ms / new_ms if new_ms > 0 else float("inf")

        assert old_rows == new_rows, f"Row count mismatch: {old_rows} vs {new_rows}"
        print(f"{label:<10} {len(data):>10,} {old_ms:>10.1f} {new_ms:>10.1f} {speedup:>9.2f}x {new_rows:>12,}")


if __name__ == "__main__":
    main()
