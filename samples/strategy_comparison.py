"""Strategy comparison example — evaluate multiple strategies side by side.

Demonstrates:
- Running simulate() across several strategies on the same data
- Collecting summary metrics into a comparison table
- Printing side-by-side performance (win rate, profit factor, Sharpe, drawdown)

Note: The included sample data is small (~90 rows, 1 month). With a larger
dataset you will see more trades and richer metrics.
"""

import os

import pandas as pd

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

    # Define strategies to compare
    strategies = [
        ("Long Calls", op.long_calls),
        ("Short Puts", op.short_puts),
        ("Long Put Spread", op.long_put_spread),
        ("Iron Condor", op.iron_condor),
    ]

    # Common parameters
    common_kwargs = {
        "capital": 100_000.0,
        "quantity": 1,
        "max_positions": 1,
        "max_entry_dte": 90,
        "exit_dte": 0,
        "commission": op.Commission(per_contract=0.65),
    }

    # Metrics to compare
    metric_keys = [
        "total_trades",
        "win_rate",
        "profit_factor",
        "total_pnl",
        "sharpe_ratio",
        "max_drawdown",
    ]

    print("=" * 60)
    print("STRATEGY COMPARISON")
    print("=" * 60)

    rows = []
    for name, strategy_fn in strategies:
        try:
            result = op.simulate(data, strategy=strategy_fn, **common_kwargs)
            row = {"strategy": name}
            for key in metric_keys:
                row[key] = result.summary.get(key)
            rows.append(row)
            print(f"  {name}: {result.summary.get('total_trades', 0)} trades")
        except Exception as e:
            print(f"  {name}: skipped ({e})")

    if not rows:
        print("\nNo strategies produced results with the sample data.")
        return

    # Build comparison table
    df = pd.DataFrame(rows).set_index("strategy")

    print("\n" + "-" * 60)
    print("Side-by-Side Comparison:")
    print("-" * 60)

    # Format floats for readability
    formatters = {
        "total_trades": lambda x: f"{x:.0f}" if pd.notna(x) else "N/A",
        "win_rate": lambda x: f"{x:.2%}" if pd.notna(x) else "N/A",
        "profit_factor": lambda x: f"{x:.2f}" if pd.notna(x) else "N/A",
        "total_pnl": lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A",
        "sharpe_ratio": lambda x: f"{x:.2f}" if pd.notna(x) else "N/A",
        "max_drawdown": lambda x: f"{x:.2%}" if pd.notna(x) else "N/A",
    }

    print(df.to_string(formatters=formatters))


if __name__ == "__main__":
    main()
