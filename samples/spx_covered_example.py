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

    # Backtest covered strategies on the SPX
    # Note: These use synthetic positions (deep ITM options) to simulate
    # the underlying stock position

    print("=" * 70)
    print("COVERED STRATEGIES (Synthetic)")
    print("=" * 70)

    # Covered Call
    # Long underlying (simulated via long deep ITM call) + short OTM call
    # Income strategy that caps upside but generates premium
    covered_call = op.covered_call(spx_data).round(2)
    print("\n1. Covered Call")
    print("-" * 50)
    print(
        tb.tabulate(
            covered_call,
            headers=covered_call.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Protective Put (Married Put)
    # Long underlying (simulated via long deep ITM call) + long OTM put
    # Provides downside protection while maintaining upside potential
    protective_put = op.protective_put(spx_data).round(2)
    print("\n2. Protective Put (Married Put)")
    print("-" * 50)
    print(
        tb.tabulate(
            protective_put,
            headers=protective_put.columns,
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
