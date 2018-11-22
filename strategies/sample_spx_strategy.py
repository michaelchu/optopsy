import os
from datetime import datetime
import pandas as pd
from optopsy.option_strategies import short_call_spread
from optopsy.statistics import show
from optopsy.data import get


def run_strategy(data):
    # define the entry and exit filters to use for this strategy, full list of
    # filters will be listed in the documentation (WIP).
    filters = {
        "start_date": datetime(2016, 1, 1),
        "end_date": datetime(2016, 12, 31),
        "entry_dte": (27, 30, 31),
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
        "contract_size": 10,
    }

    # set the start and end dates for the backtest, the dates are inclusive,
    # start and end dates are python datetime objects.
    # strategy functions will return a dataframe containing all the simulated trades
    return short_call_spread(data, filters, fill="market")


def store_and_get_data(file_name):
    # absolute file path to our input file
    curr_file = os.path.abspath(os.path.dirname(__file__))
    file = os.path.join(curr_file, "data", f"{file_name}.pkl")

    # check if we have a pickle store
    if os.path.isfile(file):
        print("pickle file found, retrieving...")
        return pd.read_pickle(file)
    else:
        print("no picked file found, retrieving csv data...")

        csv_file = os.path.join(curr_file, "data", f"{file_name}.csv")
        data = get(csv_file, SPX_FILE_STRUCT, prompt=False)

        print("storing to pickle file...")
        pd.to_pickle(data, file)
        return data


if __name__ == "__main__":
    # Here we define the struct to match the format of our csv file
    # the struct indices are 0-indexed where first column of the csv file
    # is mapped to 0
    SPX_FILE_STRUCT = (
        ("underlying_symbol", 0),
        ("underlying_price", 1),
        ("option_symbol", 3),
        ("option_type", 5),
        ("expiration", 6),
        ("quote_date", 7),
        ("strike", 8),
        ("bid", 10),
        ("ask", 11),
        ("delta", 15),
        ("gamma", 16),
        ("theta", 17),
        ("vega", 18),
    )

    # retrieve the data from pickle file if available,
    # otherwise read in the csv file
    print(store_and_get_data("SPX_2016").pipe(run_strategy).pipe(show).head())
