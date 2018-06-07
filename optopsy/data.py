import glob
import os
import sys
from distutils.util import strtobool

import pandas as pd

# All data feeds should have certain fields present, as defined by
# the second item of each tuple in the fields list, True means this field is required
fields = (
    ('symbol', True),
    ('option_symbol', False),
    ('quote_date', True),
    ('root', False),
    ('style', False),
    ('expiration', True),
    ('strike', True),
    ('option_type', True),
    ('volume', False),
    ('bid', True),
    ('ask', True),
    ('underlying_price', False),
    ('oi', False),
    ('iv', False),
    ('delta', False),
    ('gamma', False),
    ('theta', False),
    ('vega', False),
    ('rho', False)
)


def get(file_path, start, end, struct, skiprows=1, prompt=True):
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

    if os.path.isdir(file_path):
        raise ValueError("Invalid path, please provide a valid path to a file")
    else:
        cols = _check_structs(struct, start, end)
        df = pd.read_csv(file_path,
                         parse_dates=True,
                         names=cols[0],
                         usecols=cols[1],
                         skiprows=skiprows
                         )

        print(df.head())

        if prompt and user_prompt("Does this look correct?"):
            return _format(df).loc[start:end]
        elif not prompt:
            return _format(df).loc[start:end]
        else:
            sys.exit()


def gets(dir_path, start, end, struct, skiprows=1, prompt=True):
    """
    This method will read in a directory containing data files to be imported
    into a dataframe

    :file_path: the path of the directory containing the import files
    :start: date object representing the start date to include in the backtest
    :end: date object representing the end date to include in the backtest
    :struct: a list of dictionaries to describe the column index to read in the option chain data
    """

    if not os.path.isdir(dir_path):
        raise ValueError("Invalid path, please provide a valid directory path")
    else:
        cols = _check_structs(struct, start, end)

        # for each file in path
        all_files = glob.glob(os.path.join(dir_path, "*.csv"))
        all_files.sort()
        df = pd.concat(pd.read_csv(f,
                                   parse_dates=True,
                                   names=cols[0],
                                   usecols=cols[1],
                                   skiprows=skiprows
                                   ) for f in all_files
                       )

        print(df.head())

        if prompt and user_prompt("Does this look correct?"):
            return _format(df).loc[start:end]
        elif not prompt:
            return _format(df).loc[start:end]
        else:
            sys.exit()


def _format(dataframe):
    """
    Format the data frame to a standard format
    :param dataframe: dataframe to format
    :return: formatted dataframe
    """
    dataframe['expiration'] = pd.to_datetime(dataframe['expiration'], infer_datetime_format=True, format='%Y-%m-%d')
    dataframe['quote_date'] = pd.to_datetime(dataframe['quote_date'], infer_datetime_format=True, format='%Y-%m-%d')

    # convert option types to standard format 'c' or 'p'
    dataframe['option_type'] = dataframe['option_type'].str.lower().str[:1]

    # use quote date as index
    dataframe.set_index('quote_date', inplace=True)

    # rounds numbers to two decimals
    dataframe = dataframe.round(2)

    return dataframe


def _check_structs(struct, start, end):
    """
    This method will check the provided struct for this data set and make sure the
    provided fields and indices are valid
    :param start: the start date to import data
    :param end: the end date of all imported data
    :param struct: a list containing tuples that contain the column name and the index referring to the column
    number to import from
    :return:True or False
    """

    std_fields = list(zip(*fields))[0]
    req_fields = [x[0] for x in fields if x[1] is True]

    # First we check if the provided struct uses our standard list of defined column names
    for f in struct:
        if f[0] not in std_fields or f[1] < 0 or start > end:
            raise ValueError("Field names or field indices not valid!")

    cols = list(zip(*struct))

    # check if we have any duplicate indices, which would be invalid
    if len(list(set(cols[1]))) != len(cols[1]):
        raise ValueError("Duplicate indices found!")

    # Check if the struct provided contains all the required fields
    if not all(f in cols[0] for f in req_fields):
        raise ValueError("Required field names not defined!")

    return cols


def user_prompt(question):
    """
    Prompts a Yes/No questions.
    :param question: The question to ask the user
    """
    while True:
        sys.stdout.write(question + " [y/n]: ")
        user_input = input().lower()
        try:
            result = strtobool(user_input)
            return result
        except ValueError:
            sys.stdout.write("Please use y/n or yes/no.\n")
