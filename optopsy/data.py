import glob
import os
import sys
import pandas as pd
from distutils.util import strtobool


# All recognized fields by the library are defined in the tuples below. Structs are used
# to map headers from source data to one of the recognized fields.
# The second item of each tuple defines if that field is required or not
# The third item of each tuple defines the expected value type of the field. This
# is used internally in the library and should not be changed.
# The fourth item of each tuple defines if the field is affected by ratios

fields = (
    ('option_symbol', False, 'text', 'common'),
    ('underlying_symbol', True, 'text', 'common'),
    ('quote_date', True, 'date', 'common'),
    ('expiration', True, 'date', 'common'),
    ('strike', True, 'numeric', 'common'),
    ('option_type', True, 'text', 'common'),
    ('bid', True, 'numeric', 'leg'),
    ('ask', True, 'numeric', 'leg'),
    ('underlying_price', True, 'numeric', 'common'),
    ('implied_vol', False, 'numeric', 'common'),
    ('delta', True, 'numeric', 'leg'),
    ('gamma', True, 'numeric', 'leg'),
    ('theta', True, 'numeric', 'leg'),
    ('vega', True, 'numeric', 'leg'),
    ('rho', False, 'numeric', 'leg')
)


def _read_file(path, names, usecols, date_cols, skiprow, nrows=None):
    return pd.read_csv(
        path,
        names=names,
        usecols=usecols,
        parse_dates=date_cols,
        skiprows=skiprow,
        nrows=nrows,
        infer_datetime_format=True)


def _import_file(path, names, usecols, date_cols, skiprow):
    if _check_file_exists(path):
        return _read_file(path, names, usecols, date_cols,
                          skiprow).pipe(format_option_df)


def _import_dir_files(path, names, usecols, date_cols, skiprow):
    if _check_file_path_exists(path):
        fls = sorted(glob.glob(os.path.join(path, "*.csv")))
        return pd.concat(_read_file(f, names, usecols, date_cols, skiprow)
                         for f in fls).pipe(format_option_df)


def _check_file_exists(path):
    if os.path.isdir(path):
        raise ValueError("Invalid path, please provide a valid path to a file")
    return True


def _check_file_path_exists(path):
    if not os.path.isdir(path):
        raise ValueError("Invalid path, please provide a valid directory path")
    return True


def _do_preview(path, names, usecols, date_cols, skiprow):
    print(_read_file(path, names, usecols, date_cols, skiprow, nrows=5)
          .pipe(format_option_df).head()
          )
    return _user_prompt("Does this look correct?")


def get(file_path, struct, skiprow=1, prompt=True):
    return _do_import(file_path, struct, skiprow, prompt, bulk=False)


def gets(dir_path, struct, skiprow=1, prompt=True):
    return _do_import(dir_path, struct, skiprow, prompt, bulk=True)


def _do_import(path, struct, skiprow, prompt, bulk):
    cols = list(zip(*struct))
    quote_date_idx = cols[0].index('quote_date')
    expiration_idx = cols[0].index('expiration')
    date_cols = [quote_date_idx, expiration_idx]

    if _check_structs(struct, cols):
        names = cols[0]
        usecols = cols[1]
        if not prompt or (prompt & _do_preview(
                path, names, usecols, date_cols, skiprow)):
            if bulk:
                return _import_dir_files(
                    path, names, usecols, date_cols, skiprow)
            else:
                return _import_file(path, names, usecols, date_cols, skiprow)
        else:
            sys.exit()


def format_option_df(df):
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
                format='%Y-%m-%d'),
            quote_date=lambda r: pd.to_datetime(
                r['quote_date'],
                format='%Y-%m-%d'),
            option_type=lambda r: r['option_type'].str.lower().str[:1]
        )
        .assign(dte=lambda r: (r['expiration'] - r['quote_date']).dt.days)
        .round(2)
    )


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
