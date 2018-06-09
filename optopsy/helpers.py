import re

import pandas as pd


def generate_symbol(sym, exp, strike, opt_type):
    """
    The OCC option symbol consists of 4 parts:

        - Root symbol of the underlying stock or ETF, padded with spaces to 6 characters
        - Expiration date, 6 digits in the format yymmdd
        - Option type, either P or C, for put or call
        - Strike price, as the price x 1000, front padded with 0s to 8 digits
    """

    # remove any non alphabetic characters from symbol
    regex = re.compile('[^a-zA-Z]')
    sym = regex.sub('', sym).upper()

    # format the expiration date with 6 digits, no space, two characters
    expiration = pd.to_datetime(exp).strftime("%y%m%d")

    # format option type to be one char, capitalized
    valid = ('c', 'p', 'call', 'put')
    if opt_type.lower() not in valid:
        raise ValueError("Invalid option type character!")
    else:
        opt_type = opt_type[:1].upper()

    # format strike to be 8 digits padded, with strike price multiplied by 1000
    strike = "{0:0>8}".format(int(strike * 1000))

    return "%s%s%s%s" % (sym, expiration, opt_type, strike)


def parse_symbol(sym):
    """
    Parse an option symbol and return its components
    :param sym: the symbol to parse
    :return: An array of group object with various parts of the symbol parsed
    """
    matcher = re.compile(r'^([A-Z]{0,5})(7{1})?([0-9]{6})([PC])([0-9]+)$')
    return matcher.search(sym)
