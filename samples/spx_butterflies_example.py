import os
import optopsy as op
import tabulate as tb


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

    # Backtest butterfly strategies on the SPX
    # Butterflies are 3-leg strategies with equal-width wings

    print("=" * 70)
    print("BUTTERFLY STRATEGIES")
    print("=" * 70)

    # Long Call Butterfly
    # Buy 1 lower strike, sell 2 middle strike, buy 1 higher strike (all calls)
    long_call_butterfly = op.long_call_butterfly(spx_data).round(2)
    print("\n1. Long Call Butterfly")
    print("-" * 50)
    print(
        tb.tabulate(
            long_call_butterfly,
            headers=long_call_butterfly.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Long Put Butterfly
    # Buy 1 lower strike, sell 2 middle strike, buy 1 higher strike (all puts)
    long_put_butterfly = op.long_put_butterfly(spx_data).round(2)
    print("\n2. Long Put Butterfly")
    print("-" * 50)
    print(
        tb.tabulate(
            long_put_butterfly,
            headers=long_put_butterfly.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Short Call Butterfly
    # Sell 1 lower strike, buy 2 middle strike, sell 1 higher strike (all calls)
    short_call_butterfly = op.short_call_butterfly(spx_data).round(2)
    print("\n3. Short Call Butterfly")
    print("-" * 50)
    print(
        tb.tabulate(
            short_call_butterfly,
            headers=short_call_butterfly.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Short Put Butterfly
    # Sell 1 lower strike, buy 2 middle strike, sell 1 higher strike (all puts)
    short_put_butterfly = op.short_put_butterfly(spx_data).round(2)
    print("\n4. Short Put Butterfly")
    print("-" * 50)
    print(
        tb.tabulate(
            short_put_butterfly,
            headers=short_put_butterfly.columns,
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
