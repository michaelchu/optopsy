import pytest
import pandas as pd
import datetime as datetime


@pytest.fixture(scope="module")
def data():
    exp_date = datetime.datetime(2018, 1, 31)
    quote_dates = [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)]
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    d = [
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 212.5, 7.35, 7.45],
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 215.0, 6.00, 6.05],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 212.5, 5.70, 5.80],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 215.0, 7.10, 7.20],
        ["SPX", 220, "call", exp_date, quote_dates[1], 212.5, 7.45, 7.55],
        ["SPX", 220, "call", exp_date, quote_dates[1], 215.0, 4.96, 5.05],
        ["SPX", 220, "put", exp_date, quote_dates[1], 212.5, 0.0, 0.0],
        ["SPX", 220, "put", exp_date, quote_dates[1], 215.0, 0.0, 0.0],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture(scope="module")
def multi_strike_data():
    """
    Test data with multiple strikes for butterfly and iron condor strategies.
    Strikes: 207.5, 210.0, 212.5, 215.0, 217.5 (equidistant by 2.5)
    Underlying price at entry: 212.5 (ATM)
    Underlying price at exit: 215.0 (moved up)
    """
    exp_date = datetime.datetime(2018, 1, 31)
    quote_dates = [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)]
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    # Entry prices (quote_date[0], underlying at 212.5)
    # Call prices decrease as strike increases (ITM -> OTM)
    # Put prices increase as strike increases (OTM -> ITM)
    d = [
        # Entry day - Calls
        ["SPX", 212.5, "call", exp_date, quote_dates[0], 207.5, 6.90, 7.00],
        ["SPX", 212.5, "call", exp_date, quote_dates[0], 210.0, 4.90, 5.00],
        ["SPX", 212.5, "call", exp_date, quote_dates[0], 212.5, 3.00, 3.10],
        ["SPX", 212.5, "call", exp_date, quote_dates[0], 215.0, 1.50, 1.60],
        ["SPX", 212.5, "call", exp_date, quote_dates[0], 217.5, 0.60, 0.70],
        # Entry day - Puts
        ["SPX", 212.5, "put", exp_date, quote_dates[0], 207.5, 0.40, 0.50],
        ["SPX", 212.5, "put", exp_date, quote_dates[0], 210.0, 1.40, 1.50],
        ["SPX", 212.5, "put", exp_date, quote_dates[0], 212.5, 3.00, 3.10],
        ["SPX", 212.5, "put", exp_date, quote_dates[0], 215.0, 5.00, 5.10],
        ["SPX", 212.5, "put", exp_date, quote_dates[0], 217.5, 7.00, 7.10],
        # Exit day (expiration) - underlying at 215.0
        # Calls: intrinsic value = max(0, underlying - strike)
        # Puts: intrinsic value = max(0, strike - underlying)
        ["SPX", 215.0, "call", exp_date, quote_dates[1], 207.5, 7.45, 7.55],
        ["SPX", 215.0, "call", exp_date, quote_dates[1], 210.0, 4.95, 5.05],
        ["SPX", 215.0, "call", exp_date, quote_dates[1], 212.5, 2.45, 2.55],
        ["SPX", 215.0, "call", exp_date, quote_dates[1], 215.0, 0.0, 0.10],
        ["SPX", 215.0, "call", exp_date, quote_dates[1], 217.5, 0.0, 0.05],
        # Exit day - Puts (all OTM, worthless)
        ["SPX", 215.0, "put", exp_date, quote_dates[1], 207.5, 0.0, 0.05],
        ["SPX", 215.0, "put", exp_date, quote_dates[1], 210.0, 0.0, 0.05],
        ["SPX", 215.0, "put", exp_date, quote_dates[1], 212.5, 0.0, 0.05],
        ["SPX", 215.0, "put", exp_date, quote_dates[1], 215.0, 0.0, 0.05],
        ["SPX", 215.0, "put", exp_date, quote_dates[1], 217.5, 2.45, 2.55],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture(scope="module")
def data_with_delta():
    """
    Test data with delta Greek column for testing delta filtering and grouping.
    Similar to basic data fixture but includes delta values.
    """
    exp_date = datetime.datetime(2018, 1, 31)
    quote_dates = [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)]
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]
    d = [
        # Entry day - Calls (delta positive, decreasing as strike increases)
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 212.5, 7.35, 7.45, 0.60],
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 215.0, 6.00, 6.05, 0.45],
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 217.5, 4.50, 4.60, 0.30],
        # Entry day - Puts (delta negative, becoming more negative as strike increases)
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 212.5, 5.70, 5.80, -0.40],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 215.0, 7.10, 7.20, -0.55],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 217.5, 8.80, 8.90, -0.70],
        # Exit day - Calls (deltas move toward 1 or 0 at expiration)
        ["SPX", 220, "call", exp_date, quote_dates[1], 212.5, 7.45, 7.55, 0.95],
        ["SPX", 220, "call", exp_date, quote_dates[1], 215.0, 4.96, 5.05, 0.90],
        ["SPX", 220, "call", exp_date, quote_dates[1], 217.5, 2.45, 2.55, 0.80],
        # Exit day - Puts (deltas move toward -1 or 0 at expiration)
        ["SPX", 220, "put", exp_date, quote_dates[1], 212.5, 0.0, 0.05, -0.05],
        ["SPX", 220, "put", exp_date, quote_dates[1], 215.0, 0.0, 0.05, -0.10],
        ["SPX", 220, "put", exp_date, quote_dates[1], 217.5, 0.0, 0.05, -0.20],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture(scope="module")
def data_with_volume():
    """
    Test data with volume column for testing liquidity-based slippage.
    Similar to basic data fixture but includes volume values.
    """
    exp_date = datetime.datetime(2018, 1, 31)
    quote_dates = [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)]
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "volume",
    ]
    d = [
        # Entry day - Calls with varying volume
        [
            "SPX",
            213.93,
            "call",
            exp_date,
            quote_dates[0],
            212.5,
            7.35,
            7.45,
            2000,
        ],  # high vol
        [
            "SPX",
            213.93,
            "call",
            exp_date,
            quote_dates[0],
            215.0,
            6.00,
            6.10,
            100,
        ],  # low vol
        # Entry day - Puts with varying volume
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 212.5, 5.70, 5.80, 1500],
        [
            "SPX",
            213.93,
            "put",
            exp_date,
            quote_dates[0],
            215.0,
            7.10,
            7.20,
            50,
        ],  # very low vol
        # Exit day - Calls
        ["SPX", 220, "call", exp_date, quote_dates[1], 212.5, 7.45, 7.55, 3000],
        ["SPX", 220, "call", exp_date, quote_dates[1], 215.0, 4.96, 5.06, 200],
        # Exit day - Puts
        ["SPX", 220, "put", exp_date, quote_dates[1], 212.5, 0.0, 0.10, 1000],
        ["SPX", 220, "put", exp_date, quote_dates[1], 215.0, 0.0, 0.10, 100],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture(scope="module")
def calendar_data():
    """
    Test data with multiple expirations for testing calendar and diagonal spreads.

    Structure:
    - Entry date: 2018-01-01
    - Exit date: 2018-01-24 (7 days before front expiration)
    - Front month expiration: 2018-01-31 (30 DTE at entry)
    - Back month expiration: 2018-03-02 (60 DTE at entry)
    - Underlying price at entry: 212.5 (ATM)
    - Underlying price at exit: 215.0 (moved up)

    Strikes: 210.0, 212.5, 215.0
    """
    front_exp = datetime.datetime(2018, 1, 31)  # 30 DTE from entry
    back_exp = datetime.datetime(2018, 3, 2)  # 60 DTE from entry
    entry_date = datetime.datetime(2018, 1, 1)
    exit_date = datetime.datetime(2018, 1, 24)  # 7 days before front exp

    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]

    d = [
        # ===== ENTRY DATE (2018-01-01) =====
        # Front month calls (30 DTE) - lower premium due to less time value
        ["SPX", 212.5, "call", front_exp, entry_date, 210.0, 4.40, 4.50],
        ["SPX", 212.5, "call", front_exp, entry_date, 212.5, 2.90, 3.00],
        ["SPX", 212.5, "call", front_exp, entry_date, 215.0, 1.70, 1.80],
        # Front month puts (30 DTE)
        ["SPX", 212.5, "put", front_exp, entry_date, 210.0, 1.90, 2.00],
        ["SPX", 212.5, "put", front_exp, entry_date, 212.5, 2.90, 3.00],
        ["SPX", 212.5, "put", front_exp, entry_date, 215.0, 4.20, 4.30],
        # Back month calls (60 DTE) - higher premium due to more time value
        ["SPX", 212.5, "call", back_exp, entry_date, 210.0, 6.40, 6.50],
        ["SPX", 212.5, "call", back_exp, entry_date, 212.5, 4.90, 5.00],
        ["SPX", 212.5, "call", back_exp, entry_date, 215.0, 3.60, 3.70],
        # Back month puts (60 DTE)
        ["SPX", 212.5, "put", back_exp, entry_date, 210.0, 3.40, 3.50],
        ["SPX", 212.5, "put", back_exp, entry_date, 212.5, 4.90, 5.00],
        ["SPX", 212.5, "put", back_exp, entry_date, 215.0, 6.60, 6.70],
        # ===== EXIT DATE (2018-01-24) =====
        # Front month calls (7 DTE remaining) - time decay accelerated
        ["SPX", 215.0, "call", front_exp, exit_date, 210.0, 5.40, 5.50],
        ["SPX", 215.0, "call", front_exp, exit_date, 212.5, 3.00, 3.10],
        ["SPX", 215.0, "call", front_exp, exit_date, 215.0, 0.80, 0.90],
        # Front month puts (7 DTE remaining) - OTM, mostly decayed
        ["SPX", 215.0, "put", front_exp, exit_date, 210.0, 0.10, 0.20],
        ["SPX", 215.0, "put", front_exp, exit_date, 212.5, 0.30, 0.40],
        ["SPX", 215.0, "put", front_exp, exit_date, 215.0, 0.90, 1.00],
        # Back month calls (37 DTE remaining) - still has time value
        ["SPX", 215.0, "call", back_exp, exit_date, 210.0, 6.90, 7.00],
        ["SPX", 215.0, "call", back_exp, exit_date, 212.5, 5.00, 5.10],
        ["SPX", 215.0, "call", back_exp, exit_date, 215.0, 3.30, 3.40],
        # Back month puts (37 DTE remaining)
        ["SPX", 215.0, "put", back_exp, exit_date, 210.0, 1.40, 1.50],
        ["SPX", 215.0, "put", back_exp, exit_date, 212.5, 2.50, 2.60],
        ["SPX", 215.0, "put", back_exp, exit_date, 215.0, 4.30, 4.40],
    ]
    return pd.DataFrame(data=d, columns=cols)
