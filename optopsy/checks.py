import datetime
import logging
import operator


def _do_checks(data):
    required = {
        "underlying_symbol": "object",
        "quote_date": "datetime64[ns]",
        "expiration": "datetime64[ns]",
        "strike": ("float64", "int64"),
        "option_type": "object",
        "bid": "float64",
        "ask": "float64",
        "underlying_price": "float64",
        "delta": "float64",
    }

    if not all(col in data.columns.values for col in list(required.keys())):
        raise ValueError("Required columns missing!")

    data_types = data.dtypes.astype(str).to_dict()

    for key, val in required.items():
        if (key == "strike" and str(data_types[key]) not in val) or (
            key != "strike" and data_types[key] != val
        ):
            raise ValueError("Incorrect datatypes detected!")


def singles_checks(data):
    _do_checks(data)


def vertical_call_checks(data):
    _do_checks(data)


def vertical_put_checks(data):
    _do_checks(data)


def condor_checks(data):
    _do_checks(data)
