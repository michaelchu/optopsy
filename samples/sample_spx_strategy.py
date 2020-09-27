import os
from datetime import datetime
import pandas as pd
import optopsy as op

#     Optopsy is a lightweight library, it does not make any
#     assumptions on the format of your data. Therefore,
#     you are free to store your data however you like.
#
#     To use your data with this library,
#     convert your data set into a pandas DataFrame with
#     the following list of standard column names:
#
#     Column Name        Status
#     ---------------------------
#     option_symbol      Optional
#     underlying_symbol  Required
#     quote_date         Required
#     expiration         Required
#     strike             Required
#     option_type        Required
#     bid                Required
#     ask                Required
#     underlying_price   Required
#     implied_vol        Optional
#     delta              Required
#     gamma              Required
#     theta              Required
#     vega               Required
#     rho                Optional


def filepath():
    curr_file = os.path.abspath(os.path.dirname(__file__))
    # Manually download sample data file from http://www.deltaneutral.com/files/Sample_SPX_20151001_to_20151030.csv
    # and create a folder named 'data' in the same directory as this file
    # A sample data file format is provided at /data/sample_spx_data.csv
    return os.path.join(curr_file, "data", "SPX_20151001_to_20151030.csv")


def run_strategy():
    data = pd.read_csv(
        filepath(), parse_dates=["expiration", "quotedate"], infer_datetime_format=True
    )

    # manually rename the data header columns to the standard column names as defined above
    data.rename(
        columns={
            'underlying': 'underlying_symbol',
            'underlying_last': 'underlying_price',
            'type': 'option_type',
            'quotedate': 'quote_date'
        },
        inplace=True)

    results = (
        data.start_date(datetime(2015, 1, 1))
            .end_date(datetime(2015, 10, 30))
            .entry_dte(31)
            .delta(0.50)
            .calls()
            .pipe(op.long_call)
            .pipe(op.backtest, data)
            .exit_dte(7)
    )

    # the results variable is just a dataframe, which at this point contains all the trades
    # there are a few convenient functions in statistics.py to quickly calculate simple statistics
    # since results is a dataframe, you can analyze it however you like.
    print("Total trades: " + str(results.total_trades()))
    print("Total profit: " + str(results.total_profit()))
    print("\n")

    # print the trades,
    # NOTE: for the cost column a negative cost denotes an overall credit to the account
    # meaning it was a profitable trade.
    results.trades()


if __name__ == "__main__":
    run_strategy()
