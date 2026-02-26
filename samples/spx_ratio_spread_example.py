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
    print("RATIO SPREAD STRATEGIES")
    print("=" * 70)

    # Call Back Spread: Short 1 ITM call + long 2 OTM calls (2:1 ratio)
    # Bullish strategy that profits from large upward moves
    call_back = op.call_back_spread(spx_data).round(2)
    print("\n1. Call Back Spread (1:2 Ratio)")
    print("-" * 50)
    print(
        tb.tabulate(
            call_back,
            headers=call_back.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Put Back Spread: Short 1 ITM put + long 2 OTM puts (2:1 ratio)
    # Bearish strategy that profits from large downward moves
    put_back = op.put_back_spread(spx_data).round(2)
    print("\n2. Put Back Spread (1:2 Ratio)")
    print("-" * 50)
    print(
        tb.tabulate(
            put_back,
            headers=put_back.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Call Front Spread: Long 1 ITM call + short 2 OTM calls (1:2 ratio)
    # Neutral strategy that profits from time decay near short strike
    call_front = op.call_front_spread(spx_data).round(2)
    print("\n3. Call Front Spread (1:2 Ratio)")
    print("-" * 50)
    print(
        tb.tabulate(
            call_front,
            headers=call_front.columns,
            tablefmt="github",
            numalign="right",
        )
    )

    # Put Front Spread: Long 1 ITM put + short 2 OTM puts (1:2 ratio)
    # Neutral strategy that profits from time decay near short strike
    put_front = op.put_front_spread(spx_data).round(2)
    print("\n4. Put Front Spread (1:2 Ratio)")
    print("-" * 50)
    print(
        tb.tabulate(
            put_front,
            headers=put_front.columns,
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
