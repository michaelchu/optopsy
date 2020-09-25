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

    print("Total trades: " + str(results.total_trades()))
    print("Total profit: " + str(results.total_profit()))


if __name__ == "__main__":
    run_strategy()
