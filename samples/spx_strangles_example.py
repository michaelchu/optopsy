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

    # Backtest all strangles(long) on the SPX

    # All public optopsy functions return a regular Pandas DataFrame so you can use
    # regular pandas functions as you see fit to analyse the dataset
    strangles = op.long_strangles(spx_data).round(2)

    print("Statistics for SPX strangles from 2015-10-01 to 2015-10-30 \n")
    print(
        tb.tabulate(
            strangles,
            headers=strangles.columns,
            tablefmt="github",
            numalign="right",
        )
    )


if __name__ == "__main__":
    import timeit

    start = timeit.default_timer()

    # All the program statements
    run_strategy()

    stop = timeit.default_timer()
    execution_time = round(stop - start, 0)

    print("Program Executed in " + str(execution_time))  # It returns time in seconds
