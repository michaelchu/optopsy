"""Simulation with risk management — full backtest workflow.

Demonstrates:
- simulate() with capital allocation, position sizing, and trade selection
- Commission modeling with Commission()
- Spread-based slippage with fill_ratio
- Early exits: stop_loss, take_profit, max_hold_days
- SimulationResult: summary metrics, trade log, equity curve
- Exit type distribution analysis
- Standalone compute_risk_metrics() for custom analysis

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

    # --- 1. Full simulation with all risk controls ---
    print("=" * 60)
    print("SHORT PUT SIMULATION — Full Risk Management")
    print("=" * 60)

    result = op.simulate(
        data,
        strategy=op.short_puts,
        capital=100_000.0,
        quantity=1,
        max_positions=1,
        multiplier=100,
        selector="nearest",
        # Strategy parameters
        max_entry_dte=90,
        exit_dte=0,
        # Commission
        commission=op.Commission(per_contract=0.65),
        # Slippage: fill between mid and natural price
        slippage="spread",
        fill_ratio=0.5,
        # Early exits
        stop_loss=-0.20,
        take_profit=0.50,
        max_hold_days=30,
    )

    # --- 2. Performance summary ---
    print("\nPerformance Summary:")
    print("-" * 40)
    summary = result.summary
    for key in [
        "total_trades",
        "winning_trades",
        "losing_trades",
        "win_rate",
        "profit_factor",
        "total_pnl",
        "total_return",
        "sharpe_ratio",
        "sortino_ratio",
        "max_drawdown",
    ]:
        if key in summary:
            val = summary[key]
            if isinstance(val, float):
                print(f"  {key:.<30} {val:.4f}")
            else:
                print(f"  {key:.<30} {val}")

    # --- 3. Trade log ---
    print("\nTrade Log (first 5 trades):")
    print("-" * 40)
    cols = [
        "trade_id",
        "entry_date",
        "exit_date",
        "days_held",
        "realized_pnl",
        "exit_type",
    ]
    available = [c for c in cols if c in result.trade_log.columns]
    print(result.trade_log[available].head().to_string(index=False))

    # --- 4. Exit type distribution ---
    if "exit_type" in result.trade_log.columns:
        print("\nExit Type Distribution:")
        print("-" * 40)
        dist = result.trade_log["exit_type"].value_counts()
        for exit_type, count in dist.items():
            print(f"  {exit_type:.<30} {count}")

    # --- 5. Standalone risk metrics on the trade returns ---
    print("\n" + "=" * 60)
    print("STANDALONE RISK METRICS")
    print("=" * 60)
    if len(result.trade_log) > 1:
        returns = result.trade_log["pct_change"]
        metrics = op.compute_risk_metrics(
            returns,
            equity=result.equity_curve,
        )
        for key, val in metrics.items():
            if isinstance(val, float):
                print(f"  {key:.<30} {val:.4f}")
            else:
                print(f"  {key:.<30} {val}")
    else:
        print("  Not enough trades for risk analysis.")


if __name__ == "__main__":
    main()
