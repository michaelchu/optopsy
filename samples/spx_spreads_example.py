import os

import tabulate as tb

import optopsy as op


def filepath():
    curr_file = os.path.abspath(os.path.dirname(__file__))

    # This sample data file is included in the repository for demonstration.
    # For real backtesting, download your own data from sites such as:
    # CBOE Datashop: https://datashop.cboe.com/
    # HistoricalOptionData: https://www.historicaloptiondata.com/
    # DeltaNeutral: http://www.deltaneutral.com/
    return os.path.join(curr_file, "./data/sample_spx_data.csv")


def run_strategy():

    # indices for the column params are 0-indexed
    spx_data = op.csv_data(
        filepath(),
        underlying_symbol=0,
        underlying_price=1,
        option_type=5,
        expiration=6,
        quote_date=7,
        strike=8,
        bid=10,
        ask=11,
    )

    # Backtest vertical spreads on the SPX
    # Vertical spreads involve buying and selling options at different strikes
    # but with the same expiration

    print("=" * 70)
    print("VERTICAL SPREAD STRATEGIES")
    print("=" * 70)

    # Long Call Spread (Bull Call Spread)
    # Buy lower strike call, sell higher strike call
    long_call_spreads = op.long_call_spread(spx_data).round(2)
    print("\n1. Long Call Spread (Bull Call Spread)")
    print("-" * 50)
    print(
        tb.tabulate(
            long_call_spreads,
            headers=long_call_spreads.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Long Put Spread (Bear Put Spread)
    # Buy higher strike put, sell lower strike put
    long_put_spreads = op.long_put_spread(spx_data).round(2)
    print("\n2. Long Put Spread (Bear Put Spread)")
    print("-" * 50)
    print(
        tb.tabulate(
            long_put_spreads,
            headers=long_put_spreads.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Short Call Spread (Bear Call Spread)
    # Sell lower strike call, buy higher strike call
    short_call_spreads = op.short_call_spread(spx_data).round(2)
    print("\n3. Short Call Spread (Bear Call Spread)")
    print("-" * 50)
    print(
        tb.tabulate(
            short_call_spreads,
            headers=short_call_spreads.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Short Put Spread (Bull Put Spread)
    # Sell higher strike put, buy lower strike put
    short_put_spreads = op.short_put_spread(spx_data).round(2)
    print("\n4. Short Put Spread (Bull Put Spread)")
    print("-" * 50)
    print(
        tb.tabulate(
            short_put_spreads,
            headers=short_put_spreads.columns,
            tablefmt="github",
            numalign="right",
        )
    )


if __name__ == "__main__":
    import timeit

    start = timeit.default_timer()

    run_strategy()

    stop = timeit.default_timer()
    execution_time = round(stop - start, 2)

    print(f"\nProgram Executed in {execution_time}s")
