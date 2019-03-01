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


def run_strategy():

    # grab our data created externally
    curr_file = os.path.abspath(os.path.dirname(__file__))
    file = os.path.join(curr_file, "data", "SPX_2014_2018.pkl")
    data = pd.read_pickle(file)

    # define the entry and exit filters to use for this strategy, full list of
    # filters will be listed in the documentation (WIP).
    filters = {
        # set the start and end dates for the backtest,
        # the dates are inclusive, and are python datetime objects.
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 12, 31),
        # filter values can be int, float, or tuple types
        # tuples are of the following format: (min, ideal, max)
        "entry_dte": (40, 47, 50),
        "leg1_delta": 0.30,
        "contract_size": 1,
        "expr_type": "SPXW",
    }

    # strategy functions will return an optopsy dataframe
    # containing all the simulated trades
    spreads = op.long_call(data, filters)
    spreads.stats()


if __name__ == "__main__":
    run_strategy()
