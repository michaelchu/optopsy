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

    # Backtest iron condor and iron butterfly strategies on the SPX
    # These are 4-leg strategies combining puts and calls

    print("=" * 70)
    print("IRON CONDOR & IRON BUTTERFLY STRATEGIES")
    print("=" * 70)

    # Iron Condor
    # Long put (lowest), short put, short call, long call (highest)
    # Profits when underlying stays between the short strikes
    iron_condor = op.iron_condor(spx_data).round(2)
    print("\n1. Iron Condor")
    print("-" * 50)
    print(
        tb.tabulate(
            iron_condor,
            headers=iron_condor.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Reverse Iron Condor
    # Short put (lowest), long put, long call, short call (highest)
    # Profits when underlying moves significantly in either direction
    reverse_iron_condor = op.reverse_iron_condor(spx_data).round(2)
    print("\n2. Reverse Iron Condor")
    print("-" * 50)
    print(
        tb.tabulate(
            reverse_iron_condor,
            headers=reverse_iron_condor.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Iron Butterfly
    # Long put (wing), short put & short call at same strike (body), long call (wing)
    # Similar to iron condor but middle strikes are the same
    iron_butterfly = op.iron_butterfly(spx_data).round(2)
    print("\n3. Iron Butterfly")
    print("-" * 50)
    print(
        tb.tabulate(
            iron_butterfly,
            headers=iron_butterfly.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Reverse Iron Butterfly
    # Short put (wing), long put & long call at same strike (body), short call (wing)
    reverse_iron_butterfly = op.reverse_iron_butterfly(spx_data).round(2)
    print("\n4. Reverse Iron Butterfly")
    print("-" * 50)
    print(
        tb.tabulate(
            reverse_iron_butterfly,
            headers=reverse_iron_butterfly.columns,
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
