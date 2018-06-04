import pandas as pd

# All data feeds should have a default list of data fields, with
# position set to -1 to be defined by the feed itself
default_params = (
    {'symbol', -1},
    {'underlying_price', -1},
    {'option_symbol', -1},
    {'option_type', -1},
    {'expiration', -1},
    {'quote_date', -1},
    {'strike', -1},
    {'bid', -1},
    {'ask', -1},
    {'volume', -1},
    {'oi', -1},
    {'iv', -1},
    {'delta', -1},
    {'gamma', -1},
    {'theta', -1},
    {'vega', -1},
    {'rho', -1}
)


def get(file_path, start, end, struct=default_params):
    """
    This method will read in the data file using pandas and assign the
    normalized dataframe to the class's data variable.

    Normalization means to map columns from data source to a standard
    column name that will be used in this program.

    :file_path: the path of the file relative to the current file
    :start: start date to include in the backtest
    :end: end date to include in the backtest
    :struct: a list of dictionaries to describe the column index to read in the option chain data
    """

    columns = list()
    col_names = list()

    df = pd.read_csv(file_path)

    for col in struct:
        if col[1] != -1:
            columns.append(col[1])
            col_names.append(col[0])

    dataframe = df.iloc[:, columns]
    dataframe.columns = col_names

    data = dataframe.set_index('quote_date')
    return data[(data['expiration'] >= start) & (data['expiration'] <= end)]
