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

    # Backtest diagonal spread strategies on the SPX
    # Diagonal spreads use different strikes AND different expirations
    # They combine elements of vertical and calendar spreads

    print("=" * 70)
    print("DIAGONAL SPREAD STRATEGIES")
    print("=" * 70)

    # Adjust parameters to work with sample data
    diagonal_params = {
        "front_dte_min": 30,  # Front leg: 30-55 DTE
        "front_dte_max": 55,
        "back_dte_min": 60,  # Back leg: 60-90 DTE
        "back_dte_max": 90,
        "exit_dte": 12,  # Exit when front leg has 12 DTE
    }

    # Long Call Diagonal
    # Short front-month call, long back-month call at different strikes
    long_call_diagonal = op.long_call_diagonal(spx_data, **diagonal_params).round(2)
    print("\n1. Long Call Diagonal")
    print(
        f"   (front DTE: {diagonal_params['front_dte_min']}-{diagonal_params['front_dte_max']}, "
        f"back DTE: {diagonal_params['back_dte_min']}-{diagonal_params['back_dte_max']})"
    )
    print("-" * 50)
    if long_call_diagonal.empty:
        print("   No trades matched the criteria with this sample data.")
    else:
        print(
            tb.tabulate(
                long_call_diagonal,
                headers=long_call_diagonal.columns,
                tablefmt="github",
                numalign="right",
            )
        )

    # Long Put Diagonal
    # Short front-month put, long back-month put at different strikes
    long_put_diagonal = op.long_put_diagonal(spx_data, **diagonal_params).round(2)
    print("\n2. Long Put Diagonal")
    print("-" * 50)
    if long_put_diagonal.empty:
        print("   No trades matched the criteria with this sample data.")
    else:
        print(
            tb.tabulate(
                long_put_diagonal,
                headers=long_put_diagonal.columns,
                tablefmt="github",
                numalign="right",
            )
        )

    # Short Call Diagonal
    # Long front-month call, short back-month call at different strikes
    short_call_diagonal = op.short_call_diagonal(spx_data, **diagonal_params).round(2)
    print("\n3. Short Call Diagonal")
    print("-" * 50)
    if short_call_diagonal.empty:
        print("   No trades matched the criteria with this sample data.")
    else:
        print(
            tb.tabulate(
                short_call_diagonal,
                headers=short_call_diagonal.columns,
                tablefmt="github",
                numalign="right",
            )
        )

    # Short Put Diagonal
    # Long front-month put, short back-month put at different strikes
    short_put_diagonal = op.short_put_diagonal(spx_data, **diagonal_params).round(2)
    print("\n4. Short Put Diagonal")
    print("-" * 50)
    if short_put_diagonal.empty:
        print("   No trades matched the criteria with this sample data.")
    else:
        print(
            tb.tabulate(
                short_put_diagonal,
                headers=short_put_diagonal.columns,
                tablefmt="github",
                numalign="right",
            )
        )

    print("\n" + "=" * 70)
    print("NOTE: Diagonal spreads require data spanning multiple expirations")
    print("and strikes. The sample data is limited. For comprehensive")
    print("backtesting, use a larger dataset.")
    print("=" * 70)


if __name__ == "__main__":
    import timeit

    start = timeit.default_timer()

    run_strategy()

    stop = timeit.default_timer()
    execution_time = round(stop - start, 2)

    print(f"\nProgram Executed in {execution_time}s")
