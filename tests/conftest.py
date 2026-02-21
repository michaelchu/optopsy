import datetime as datetime

import numpy as np
import pandas as pd
import pytest


def make_stock_data(
    symbol: str = "SPX",
    start: str = "2017-06-01",
    periods: int = 200,
    freq: str = "B",
    base_price: float = 200.0,
    daily_returns: list[float] | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Factory that produces yfinance-shaped OHLCV DataFrames for testing.

    Contract matches ``_fetch_stock_data_for_signals`` normalisation:
    - Columns: underlying_symbol, quote_date, open, high, low, close, volume
    - quote_date is timezone-naive datetime64
    - Business-day frequency by default
    - Deterministic: uses ``daily_returns`` if provided, else a seeded random walk

    Args:
        symbol: Underlying symbol (default "SPX")
        start: First bar date (default "2017-06-01")
        periods: Number of bars (default 200)
        freq: Pandas frequency string (default "B" for business days)
        base_price: Starting close price (default 200.0)
        daily_returns: Explicit list of fractional returns per bar.  If None
            a seeded random walk is used.  Length must equal ``periods - 1``.
        seed: Random seed for the random walk (default 42)

    Returns:
        DataFrame with columns [underlying_symbol, quote_date, open, high,
        low, close, volume], one row per bar, sorted by date.
    """
    dates = pd.date_range(start, periods=periods, freq=freq)

    if daily_returns is not None:
        assert (
            len(daily_returns) == periods - 1
        ), f"daily_returns length {len(daily_returns)} != periods-1 ({periods - 1})"
        closes = [base_price]
        for r in daily_returns:
            closes.append(closes[-1] * (1 + r))
    else:
        rng = np.random.default_rng(seed)
        returns = rng.normal(0, 0.005, size=periods - 1)
        closes = [base_price]
        for r in returns:
            closes.append(closes[-1] * (1 + r))

    closes = np.array(closes)
    # open = previous close (first bar: open == close)
    opens = np.empty_like(closes)
    opens[0] = closes[0]
    opens[1:] = closes[:-1]

    # Realistic high/low: jitter above/below max/min of open/close
    rng_hl = np.random.default_rng(seed + 1)
    jitter = rng_hl.uniform(0.001, 0.005, size=periods) * closes
    highs = np.maximum(opens, closes) + jitter
    lows = np.minimum(opens, closes) - jitter

    return pd.DataFrame(
        {
            "underlying_symbol": symbol,
            "quote_date": dates,
            "open": np.round(opens, 2),
            "high": np.round(highs, 2),
            "low": np.round(lows, 2),
            "close": np.round(closes, 2),
            "volume": 1_000_000,
        }
    )


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


@pytest.fixture
def option_data_entry_exit():
    """
    Option data with clear entry and exit dates for testing signal filtering.
    Entry date: 2018-01-04 (Thursday) with DTE=30
    Exit date: 2018-02-02 (expiration, DTE=0)

    Also includes 2018-01-03 (Wednesday) as an entry date that should be
    filtered out by day_of_week(3) (Thursday only).
    """
    entry_wed = datetime.datetime(2018, 1, 3)  # Wednesday
    entry_thu = datetime.datetime(2018, 1, 4)  # Thursday
    exp_date = datetime.datetime(2018, 2, 3)

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
        # Wednesday entry
        ["SPX", 213.93, "call", exp_date, entry_wed, 212.5, 7.35, 7.45],
        ["SPX", 213.93, "call", exp_date, entry_wed, 215.0, 6.00, 6.05],
        ["SPX", 213.93, "put", exp_date, entry_wed, 212.5, 5.70, 5.80],
        ["SPX", 213.93, "put", exp_date, entry_wed, 215.0, 7.10, 7.20],
        # Thursday entry
        ["SPX", 214.50, "call", exp_date, entry_thu, 212.5, 7.55, 7.65],
        ["SPX", 214.50, "call", exp_date, entry_thu, 215.0, 6.10, 6.20],
        ["SPX", 214.50, "put", exp_date, entry_thu, 212.5, 5.50, 5.60],
        ["SPX", 214.50, "put", exp_date, entry_thu, 215.0, 6.90, 7.00],
        # Exit (expiration)
        ["SPX", 220, "call", exp_date, exp_date, 212.5, 7.45, 7.55],
        ["SPX", 220, "call", exp_date, exp_date, 215.0, 4.96, 5.05],
        ["SPX", 220, "put", exp_date, exp_date, 212.5, 0.0, 0.05],
        ["SPX", 220, "put", exp_date, exp_date, 215.0, 0.0, 0.05],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture
def stock_data_spx():
    """Stock data matching the option_data_entry_exit fixture prices."""
    entry_wed = datetime.datetime(2018, 1, 3)
    entry_thu = datetime.datetime(2018, 1, 4)
    exp_date = datetime.datetime(2018, 2, 3)
    return pd.DataFrame(
        {
            "underlying_symbol": ["SPX"] * 3,
            "quote_date": [entry_wed, entry_thu, exp_date],
            "close": [213.93, 214.50, 220.0],
        }
    )


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


@pytest.fixture(scope="class")
def stock_data_long_history():
    """
    200-bar OHLCV stock data with a designed price pattern:
    - Bars 0–40:   decline from 220 → ~196  (RSI drops to 0)
    - Bars 41–42:  brief +2% bounce          (RSI jumps to ~51, breaks streak)
    - Bars 43–80:  resume decline → ~173     (RSI gradually drops back below 30)
    - Bars 80–140: flat around 173           (RSI neutral, price near SMA-20)
    - Bars 140–199: recovery from ~174 → ~227 (SMA crossover, RSI > 70)

    The bounce at bars 41–42 creates a gap where rsi_below(14,30) resets,
    so sustained(rsi_below(14,30), days=3) rejects bar 53 (RSI just crossed
    back below 30 for <3 bars) but accepts bar 30 (deep in the streak).

    Key bar values:
      bar 30:  RSI=0,    sma_above(20)=False, rsi_below(14,30)=True,  sustained(3)=True
      bar 53:  RSI≈29.8, sma_above(20)=False, rsi_below(14,30)=True,  sustained(3)=False
      bar 100: RSI≈14,   rsi_above(14,70)=False (exit signal rejects exp-A)
      bar 160: RSI≈99.8, sma_above(20)=True,  rsi_below(14,30)=False
      bar 170: RSI≈99.9, sma_above(20)=True,  rsi_below(14,30)=False
      bar 195: RSI≈100,  rsi_above(14,70)=True  (exit signal keeps exp-B)
    """
    n = 200
    rets: list[float] = []
    # Phase 1: decline (40 bars, -0.3%/day)
    for _ in range(40):
        rets.append(-0.003)
    # Phase 2: bounce (2 bars, +2%/day — breaks RSI streak)
    rets.append(0.02)
    rets.append(0.02)
    # Phase 3: resume decline (38 bars, -0.3%/day)
    for _ in range(38):
        rets.append(-0.003)
    # Phase 4: flat (60 bars)
    for _ in range(60):
        rets.append(0.0001)
    # Phase 5: recovery (59 bars, +0.4%/day)
    for _ in range(59):
        rets.append(0.004)
    assert len(rets) == n - 1
    return make_stock_data(
        symbol="SPX",
        start="2017-06-01",
        periods=n,
        daily_returns=rets,
        base_price=220.0,
    )


@pytest.fixture(scope="class")
def option_data_with_stock(stock_data_long_history):
    """
    Option chain whose entry/exit dates overlap with stock_data_long_history.

    Uses FIXED strikes (195, 200, 205) to avoid many-to-many merge issues
    from overlapping price-relative strikes across entry dates.

    Entry dates (4):
      - Bar 30 (decline, RSI=0, sma=False)
      - Bar 53 (post-bounce, RSI≈29.8, sma=False — sustained(3) rejects this)
      - Bar 160 (recovery, RSI≈99.8, sma=True)
      - Bar 170 (recovery, RSI≈99.9, sma=True)

    Expirations (2):
      - Exp A = bar 100 (flat phase, RSI≈14 → rsi_above(14,70) rejects)
      - Exp B = bar 195 (recovery, RSI≈100 → rsi_above(14,70) keeps)

    Recovery entries (bars 160, 170) are AFTER exp-A so they only match
    exp-B. Decline entries (bars 30, 53) can match both.

    Baseline row count for long_calls: 18
      - Bar 30: 3 calls × 2 exps = 6
      - Bar 53: 3 calls × 2 exps = 6
      - Bar 160: 3 calls × 1 exp (B only) = 3
      - Bar 170: 3 calls × 1 exp (B only) = 3
    """
    sd = stock_data_long_history
    dates = sd["quote_date"].values
    price_map = dict(zip(sd["quote_date"], sd["close"]))

    # Entry dates
    entry_decline_1 = pd.Timestamp(dates[30])  # deep in decline
    entry_decline_2 = pd.Timestamp(dates[53])  # post-bounce, RSI just < 30
    entry_recovery_1 = pd.Timestamp(dates[160])  # recovery phase
    entry_recovery_2 = pd.Timestamp(dates[170])  # recovery phase
    exit_date_a = pd.Timestamp(dates[100])  # flat phase, RSI < 70
    exit_date_b = pd.Timestamp(dates[195])  # recovery phase, RSI > 70

    # Fixed strikes — avoids many-to-many merge from overlapping price-relative strikes
    strikes = [195.0, 200.0, 205.0]

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

    rows = []
    entry_dates = [
        entry_decline_1,
        entry_decline_2,
        entry_recovery_1,
        entry_recovery_2,
    ]
    expirations = [exit_date_a, exit_date_b]

    for exp_date in expirations:
        # Entry rows for each (entry_date, expiration) pair
        for ed in entry_dates:
            price = price_map[ed]
            for strike in strikes:
                moneyness = strike - price  # positive = OTM call
                # Call premiums based on moneyness
                if moneyness < -3:
                    bid, ask = 7.0, 7.10
                elif -3 <= moneyness <= 3:
                    bid, ask = 3.5, 3.60
                else:
                    bid, ask = 1.0, 1.10
                rows.append(["SPX", price, "call", exp_date, ed, strike, bid, ask])
                # Put premiums (reverse moneyness)
                if moneyness > 3:
                    bid, ask = 7.0, 7.10
                elif -3 <= moneyness <= 3:
                    bid, ask = 3.5, 3.60
                else:
                    bid, ask = 1.0, 1.10
                rows.append(["SPX", price, "put", exp_date, ed, strike, bid, ask])

        # Single set of exit rows per expiration (no per-entry duplication)
        exit_price = price_map[exp_date]
        for strike in strikes:
            call_intrinsic = max(exit_price - strike, 0)
            rows.append(
                [
                    "SPX",
                    exit_price,
                    "call",
                    exp_date,
                    exp_date,
                    strike,
                    round(call_intrinsic, 2),
                    round(call_intrinsic + 0.05, 2),
                ]
            )
            put_intrinsic = max(strike - exit_price, 0)
            rows.append(
                [
                    "SPX",
                    exit_price,
                    "put",
                    exp_date,
                    exp_date,
                    strike,
                    round(put_intrinsic, 2),
                    round(put_intrinsic + 0.05, 2),
                ]
            )

    return pd.DataFrame(data=rows, columns=cols)
