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

    # Backtest calendar spread strategies on the SPX
    # Calendar spreads use the same strike but different expirations
    # They profit from time decay differential between near and far options

    print("=" * 70)
    print("CALENDAR SPREAD STRATEGIES")
    print("=" * 70)

    # Adjust parameters to work with sample data
    # Sample data has expirations at Oct 16, Nov 20, Dec 18
    # From Oct 1: Oct 16 = 15 DTE, Nov 20 = 50 DTE, Dec 18 = 78 DTE
    calendar_params = {
        "front_dte_min": 30,  # Front leg: 30-55 DTE (targets Nov 20 from Oct 1)
        "front_dte_max": 55,
        "back_dte_min": 60,  # Back leg: 60-90 DTE (targets Dec 18 from Oct 1)
        "back_dte_max": 90,
        "exit_dte": 12,  # Exit when front leg has 12 DTE
    }

    # Long Call Calendar
    # Short front-month call, long back-month call at same strike
    long_call_calendar = op.long_call_calendar(spx_data, **calendar_params).round(2)
    print("\n1. Long Call Calendar")
    print(f"   (front DTE: {calendar_params['front_dte_min']}-{calendar_params['front_dte_max']}, "
          f"back DTE: {calendar_params['back_dte_min']}-{calendar_params['back_dte_max']})")
    print("-" * 50)
    if long_call_calendar.empty:
        print("   No trades matched the criteria with this sample data.")
    else:
        print(
            tb.tabulate(
                long_call_calendar,
                headers=long_call_calendar.columns,
                tablefmt="github",
                numalign="right",
            )
        )

    # Long Put Calendar
    # Short front-month put, long back-month put at same strike
    long_put_calendar = op.long_put_calendar(spx_data, **calendar_params).round(2)
    print("\n2. Long Put Calendar")
    print("-" * 50)
    if long_put_calendar.empty:
        print("   No trades matched the criteria with this sample data.")
    else:
        print(
            tb.tabulate(
                long_put_calendar,
                headers=long_put_calendar.columns,
                tablefmt="github",
                numalign="right",
            )
        )

    # Short Call Calendar
    # Long front-month call, short back-month call at same strike
    short_call_calendar = op.short_call_calendar(spx_data, **calendar_params).round(2)
    print("\n3. Short Call Calendar")
    print("-" * 50)
    if short_call_calendar.empty:
        print("   No trades matched the criteria with this sample data.")
    else:
        print(
            tb.tabulate(
                short_call_calendar,
                headers=short_call_calendar.columns,
                tablefmt="github",
                numalign="right",
            )
        )

    # Short Put Calendar
    # Long front-month put, short back-month put at same strike
    short_put_calendar = op.short_put_calendar(spx_data, **calendar_params).round(2)
    print("\n4. Short Put Calendar")
    print("-" * 50)
    if short_put_calendar.empty:
        print("   No trades matched the criteria with this sample data.")
    else:
        print(
            tb.tabulate(
                short_put_calendar,
                headers=short_put_calendar.columns,
                tablefmt="github",
                numalign="right",
            )
        )

    print("\n" + "=" * 70)
    print("NOTE: Calendar spreads require data spanning multiple expirations.")
    print("The sample data is limited. For comprehensive backtesting,")
    print("use a larger dataset with more quote dates and expirations.")
    print("=" * 70)


if __name__ == "__main__":
    import timeit

    start = timeit.default_timer()

    run_strategy()

    stop = timeit.default_timer()
    execution_time = round(stop - start, 2)

    print(f"\nProgram Executed in {execution_time}s")
