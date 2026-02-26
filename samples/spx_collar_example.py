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

    print("=" * 70)
    print("COLLAR STRATEGY (Synthetic)")
    print("=" * 70)

    # Collar: Long underlying (deep ITM call) + short OTM call + long OTM put
    # Hedges downside risk while capping upside, typically for a small net credit/debit
    collar = op.collar(spx_data).round(2)
    print("\n1. Collar (Synthetic)")
    print("-" * 50)
    print(
        tb.tabulate(
            collar,
            headers=collar.columns,
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
