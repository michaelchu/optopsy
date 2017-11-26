import pandas as pd
import re


def generate_symbol(sym, exp, strike, opt_type):
    """
    The OCC option symbol consists of 4 parts:

        - Root symbol of the underlying stock or ETF, padded with spaces to 6 characters
        - Expiration date, 6 digits in the format yymmdd
        - Option type, either P or C, for put or call
        - Strike price, as the price x 1000, front padded with 0s to 8 digits
    """
    expiration = pd.to_datetime(exp).strftime("%y%m%d")
    opt_type = opt_type.upper()
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
