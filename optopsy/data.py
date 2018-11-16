#     Optopsy - Python Backtesting library for options trading strategies
#     Copyright (C) 2018  Michael Chu

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
    ("option_symbol", False),
    ("underlying_symbol", True),
    ("quote_date", True),
    ("expiration", True),
    ("strike", True),
    ("option_type", True),
    ("bid", True),
    ("ask", True),
    ("underlying_price", True),
    ("implied_vol", False),
    ("delta", True),
    ("gamma", True),
    ("theta", True),
    ("vega", True),
    ("rho", False),
)


def _import_file(path, names, usecols, date_cols, skiprow):
    if not os.path.isdir(path):
        data = pd.read_csv(
            path,
            names=names,
            usecols=usecols,
            parse_dates=date_cols,
            skiprows=skiprow,
            infer_datetime_format=True,
        )
    elif os.path.isdir(path):
        fls = sorted(glob.glob(os.path.join(path, "*.csv")))
        data = pd.concat(
            pd.read_csv(
                f, names=names, usecols=usecols, parse_dates=date_cols, skiprows=skiprow
            )
            for f in fls
        )
    else:
        raise ValueError("Invalid path, please provide a valid path to a file")

    return data.pipe(format_option_df)


def _do_preview(data):
    print(data.head())
    return _user_prompt("Does this look correct?")


def get(file_path, struct, skiprow=1, prompt=True):
    return _do_import(file_path, struct, skiprow, prompt)


def _do_import(path, struct, skiprow, prompt):
    cols = list(zip(*struct))
    date_cols = [cols[0].index("quote_date"), cols[0].index("expiration")]

    if _check_structs(struct, cols):
        data = _import_file(path, cols[0], cols[1], date_cols, skiprow)
        if not prompt or (prompt & _do_preview(data)):
            return data
        else:
            sys.exit()


def format_option_df(df):
    return (
        df.assign(
            expiration=lambda r: pd.to_datetime(r["expiration"], format="%Y-%m-%d"),
            quote_date=lambda r: pd.to_datetime(r["quote_date"], format="%Y-%m-%d"),
            option_type=lambda r: r["option_type"].str.lower().str[:1],
        )
        .assign(dte=lambda r: (r["expiration"] - r["quote_date"]).dt.days)
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
    return (
        _check_field_is_standard(struct)
        and _check_field_is_duplicated(cols)
        and _check_fields_contains_required(cols)
    )


def _user_prompt(question):
    while True:
        sys.stdout.write(question + " [y/n]: ")
        user_input = input().lower()
        try:
            result = strtobool(user_input)
            return result
        except ValueError:
            sys.stdout.write("Please use y/n or yes/no.\n")
