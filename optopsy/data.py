import glob
import os
import sys
from distutils.util import strtobool

import pandas as pd

from .helpers import generate_symbol

# All data feeds should have certain fields present, as defined by
# the second item of each tuple in the fields list, True means this field
# is required
fields = (
    ('underlying_symbol', True),
    ('option_symbol', False),
    ('quote_date', True),
    ('root', True),
    ('style', False),
    ('expiration', True),
    ('strike', True),
    ('option_type', True),
    ('volume', False),
    ('bid', True),
    ('ask', True),
    ('underlying_price', True),
    ('open_interest', False),
    ('implied_vol', False),
    ('delta', True),
    ('gamma', True),
    ('theta', True),
    ('vega', True),
    ('rho', False)
)


def _read_file(path, names, usecols, skiprow, nrows=None):
    return pd.read_csv(path, parse_dates=True, names=names, usecols=usecols, skiprows=skiprow,
                       nrows=nrows)


def _import_file(path, names, usecols, skiprow):
    if _check_file_exists(path):
        return _read_file(path, names, usecols, skiprow).pipe(_format)


def _import_dir_files(path, names, usecols, skiprow):
    if _check_file_path_exists(path):
        fls = sorted(glob.glob(os.path.join(path, "*.csv")))
        return pd.concat(_read_file(f, names, usecols, skiprow) for f in fls).pipe(_format)


def _check_file_exists(path):
    if os.path.isdir(path):
        raise ValueError("Invalid path, please provide a valid path to a file")
    return True


def _check_file_path_exists(path):
    if not os.path.isdir(path):
        raise ValueError("Invalid path, please provide a valid directory path")
    return True


def _do_preview(path, names, usecols, skiprow):
    print(_read_file(path, names, usecols, skiprow, nrows=5)
          .pipe(_format).head()
          )
    return _user_prompt("Does this look correct?")


def get(file_path, struct, skiprow=1, prompt=True):
    return _do_import(file_path, struct, skiprow, prompt, bulk=False)


def gets(dir_path, struct, skiprow=1, prompt=True):
    return _do_import(dir_path, struct, skiprow, prompt, bulk=True)


def _do_import(path, struct, skiprow, prompt, bulk):
    cols = list(zip(*struct))

    if _check_structs(struct, cols):
        names = cols[0]
        usecols = cols[1]

        if not prompt or (prompt & _do_preview(path, names, usecols, skiprow)):
            if bulk:
                return _import_dir_files(path, names, usecols, skiprow)
            else:
                return _import_file(path, names, usecols, skiprow)
        else:
            sys.exit()


def _format(df):
    """
    Format the data frame to a standard format
    :param df: dataframe to format
    :return: formatted dataframe
    """

    return (
        df
        .assign(
            expiration=lambda r: pd.to_datetime(
                r['expiration'],
                infer_datetime_format=True,
                format='%Y-%m-%d'),
            quote_date=lambda r: pd.to_datetime(
                r['quote_date'],
                infer_datetime_format=True,
                format='%Y-%m-%d'),
            option_type=lambda r: r['option_type'].str.lower().str[:1])
        .round(2)
        .pipe(_assign_option_symbol)
    )


def _assign_option_symbol(df):
    # if the data source did not include a option_symbol field, we will
    # generate it
    if 'option_symbol' in df.columns:
        return (df
                .rename(columns={'option_symbol': 'symbol'})
                .assign(symbol=lambda r: '.' + r['symbol'])
                )
    else:
        # TODO: vectorize this method, avoid using df.apply()
        return (
            df.assign(symbol=lambda r: '.' + df.apply(
                lambda r: generate_symbol(r['root'], r['expiration'], r['strike'],
                                          r['option_type']), axis=1)))


def _check_field_is_standard(struct):
    # First we check if the provided struct uses our standard list of defined
    # column names
    std_fields = list(zip(*fields))[0]
    for f in struct:
        if f[0] not in std_fields or f[1] < 0:
            raise ValueError("Field names or field indices not valid!")
    return True


def _check_field_is_duplicated(cols):
    # check if we have any duplicate indices, which would be invalid
    if len(list(set(cols[1]))) != len(cols[1]):
        raise ValueError("Duplicate indices found!")
    return True


def _check_fields_contains_required(cols):
    # Check if the struct provided contains all the required fields
    req_fields = [x[0] for x in fields if x[1] is True]
    if not all(f in cols[0] for f in req_fields):
        raise ValueError("Required field names not defined!")
    return True


def _check_structs(struct, cols):
    return (_check_field_is_standard(struct) and
            _check_field_is_duplicated(cols) and
            _check_fields_contains_required(cols))


def _user_prompt(question):
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
