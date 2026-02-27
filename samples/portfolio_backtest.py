"""Portfolio backtest example — multi-strategy allocation.

Demonstrates:
- simulate_portfolio() with multiple strategy legs on the same data
- Capital weighting across strategies
- Portfolio-level vs. per-leg performance summaries

Note: The included sample data is small (~90 rows, 1 month). With a larger
dataset you will see more trades and richer metrics.
"""

import os

import optopsy as op

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "sample_spx_data.csv")


def load_data():
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

    # --- Multi-strategy portfolio ---
    print("=" * 60)
    print("PORTFOLIO BACKTEST — Short Puts + Long Call Spreads")
    print("=" * 60)

    result = op.simulate_portfolio(
        legs=[
            {
                "data": data,
                "strategy": op.short_puts,
                "weight": 0.6,
                "name": "short_puts",
                "max_entry_dte": 90,
                "exit_dte": 0,
                "commission": op.Commission(per_contract=0.65),
            },
            {
                "data": data,
                "strategy": op.long_call_spread,
                "weight": 0.4,
                "name": "long_call_spread",
                "max_entry_dte": 90,
                "exit_dte": 0,
                "commission": op.Commission(per_contract=0.65),
            },
        ],
        capital=100_000.0,
    )

    # --- Portfolio-level summary ---
    print("\nPortfolio Summary:")
    print("-" * 40)
    for key in [
        "total_trades",
        "win_rate",
        "profit_factor",
        "total_pnl",
        "sharpe_ratio",
        "max_drawdown",
    ]:
        if key in result.summary:
            val = result.summary[key]
            if isinstance(val, float):
                print(f"  {key:.<30} {val:.4f}")
            else:
                print(f"  {key:.<30} {val}")

    # --- Per-leg summaries ---
    print("\nPer-Leg Results:")
    print("-" * 40)
    for name, leg_result in result.leg_results.items():
        s = leg_result.summary
        trades = s.get("total_trades", 0)
        pnl = s.get("total_pnl", 0)
        wr = s.get("win_rate", 0)
        print(f"  {name}: {trades} trades, PnL={pnl:.2f}, win_rate={wr:.2%}")

    # --- Combined trade log ---
    print("\nCombined Trade Log (first 5):")
    print("-" * 40)
    cols = ["trade_id", "entry_date", "exit_date", "realized_pnl"]
    available = [c for c in cols if c in result.trade_log.columns]
    if "leg" in result.trade_log.columns:
        available.insert(0, "leg")
    print(result.trade_log[available].head().to_string(index=False))


if __name__ == "__main__":
    main()
