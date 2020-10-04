import os
import optopsy as op
import tabulate as tb


def filepath():
    curr_file = os.path.abspath(os.path.dirname(__file__))

    # for demo purposes only, download your copy of data from sites such as:
    # CBOE Datashop: https://datashop.cboe.com/
    # HistoricalOptionData: https://www.historicaloptiondata.com/
    # DeltaNeutral: http://www.deltaneutral.com/

    # following file was downloaded from: http://www.deltaneutral.com/files/Sample_SPX_20151001_to_20151030.csv
    return os.path.join(curr_file, "./data/Sample_SPX_20151001_to_20151030.csv")


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

    # Backtest all single calls(long) on the SPX

    # All public optopsy functions return a regular Pandas DataFrame so you can use
    # regular pandas functions as you see fit to analyse the dataset
    long_single_calls = op.singles_calls(
        spx_data, strike_dist_pct_interval=0.05, side="long"
    ).round(2)

    print("Statistics for SPX long calls from 2015-10-01 to 2015-10-30 \n")
    print(
        tb.tabulate(
            long_single_calls,
            headers=long_single_calls.columns,
            tablefmt="github",
            numalign="right",
        )
    )


if __name__ == "__main__":
    run_strategy()
