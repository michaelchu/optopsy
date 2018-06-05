import pandas as pd

# All data feeds should have a default list of data fields, with
# position set to -1 to be defined by the feed itself
params = (
    'symbol',
    'quote_date',
    'root',
    'expiration',
    'strike',
    'option_type',
    'volume',
    'bid',
    'ask',
    'underlying_price',
    'oi',
    'iv',
    'delta',
    'gamma',
    'theta',
    'vega',
    'rho'
)


def get(file_path, start, end, struct, skiprows=1):
    """
    This method will read in the data file using pandas and assign the
    normalized dataframe to the class's data variable.

    Normalization means to map columns from data source to a standard
    column name that will be used in this program.

    :file_path: the path of the file relative to the current file
    :start: date object representing the start date to include in the backtest
    :end: date object representing the end date to include in the backtest
    :struct: a list of dictionaries to describe the column index to read in the option chain data
    """

    # First we check if the provided struct uses our standard list of defined column names
    for i in struct:
        if i[0] not in params:
            raise ValueError()

    cols = list(zip(*struct))

    df = pd.read_csv(file_path, parse_dates=True, names=cols[0], usecols=cols[1], skiprows=skiprows)

    return df
