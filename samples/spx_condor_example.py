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
    print("CONDOR STRATEGIES (Same Option Type)")
    print("=" * 70)

    # Long Call Condor: Long K1 call + short K2 call + short K3 call + long K4 call
    # Neutral strategy using only calls, profits when underlying stays in range
    long_cc = op.long_call_condor(spx_data).round(2)
    print("\n1. Long Call Condor")
    print("-" * 50)
    print(
        tb.tabulate(
            long_cc,
            headers=long_cc.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Short Call Condor: Short K1 call + long K2 call + long K3 call + short K4 call
    # Profits from large move in either direction
    short_cc = op.short_call_condor(spx_data).round(2)
    print("\n2. Short Call Condor")
    print("-" * 50)
    print(
        tb.tabulate(
            short_cc,
            headers=short_cc.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Long Put Condor: Long K1 put + short K2 put + short K3 put + long K4 put
    # Neutral strategy using only puts, profits when underlying stays in range
    long_pc = op.long_put_condor(spx_data).round(2)
    print("\n3. Long Put Condor")
    print("-" * 50)
    print(
        tb.tabulate(
            long_pc,
            headers=long_pc.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Short Put Condor: Short K1 put + long K2 put + long K3 put + short K4 put
    # Profits from large move in either direction
    short_pc = op.short_put_condor(spx_data).round(2)
    print("\n4. Short Put Condor")
    print("-" * 50)
    print(
        tb.tabulate(
            short_pc,
            headers=short_pc.columns,
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
