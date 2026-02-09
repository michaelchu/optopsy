"""Public API for options strategy generation.

This module exposes all 28 supported options strategies. Each public function
accepts a DataFrame of option chain data (produced by :func:`optopsy.datafeeds.csv_data`)
and optional keyword parameters that control filtering, grouping, and slippage.

Strategy families:
    - **Singles**: long/short calls and puts.
    - **Straddles & Strangles**: paired call + put at same or different strikes.
    - **Vertical Spreads**: bull/bear call and put spreads.
    - **Butterflies**: 3-leg strategies with equal-width wings.
    - **Iron Condors & Iron Butterflies**: 4-leg strategies combining puts and calls.
    - **Covered Strategies**: covered calls and protective puts.
    - **Calendar Spreads**: same strike, different expirations.
    - **Diagonal Spreads**: different strikes and expirations.

Common keyword arguments accepted by all strategies:
    dte_interval (int): DTE bucket width for grouping (default: 7).
    max_entry_dte (int): Maximum days-to-expiration at entry (default: 90).
    exit_dte (int): Days-to-expiration at which to exit (default: 0).
    otm_pct_interval (float): OTM percentage bucket width (default: 0.05).
    max_otm_pct (float): Maximum OTM percentage to consider (default: 0.5).
    min_bid_ask (float): Minimum bid/ask to filter worthless options (default: 0.05).
    raw (bool): Return raw trade-level data instead of grouped statistics
        (default: False).
    drop_nan (bool): Drop rows with NaN statistics (default: True).
    slippage (str): Fill-price model — ``"mid"``, ``"spread"``, or ``"liquidity"``
        (default: ``"mid"``).
    fill_ratio (float): Base fill ratio for liquidity mode, 0.0-1.0 (default: 0.5).
    reference_volume (int): Volume threshold for liquid options (default: 1000).
"""

from typing import Any, Dict, List, Tuple
import pandas as pd
from .core import _calls, _puts, _process_strategy, _process_calendar_strategy
from .definitions import (
    single_strike_external_cols,
    single_strike_internal_cols,
    double_strike_external_cols,
    double_strike_internal_cols,
    triple_strike_external_cols,
    triple_strike_internal_cols,
    quadruple_strike_external_cols,
    quadruple_strike_internal_cols,
    straddle_internal_cols,
    calendar_spread_internal_cols,
    calendar_spread_external_cols,
    diagonal_spread_internal_cols,
    diagonal_spread_external_cols,
)
from .rules import (
    _rule_non_overlapping_strike,
    _rule_butterfly_strikes,
    _rule_iron_condor_strikes,
    _rule_iron_butterfly_strikes,
    _rule_expiration_ordering,
)
from enum import Enum

default_kwargs: Dict[str, Any] = {
    "dte_interval": 7,
    "max_entry_dte": 90,
    "exit_dte": 0,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
    # Greeks filtering (optional)
    "delta_min": None,
    "delta_max": None,
    # Greeks grouping (optional)
    "delta_interval": None,
    # Slippage settings
    "slippage": "mid",  # "mid", "spread", or "liquidity"
    "fill_ratio": 0.5,  # Base fill ratio for liquidity mode (0.0-1.0)
    "reference_volume": 1000,  # Volume threshold for liquid options
}

calendar_default_kwargs: Dict[str, Any] = {
    "front_dte_min": 20,
    "front_dte_max": 40,
    "back_dte_min": 50,
    "back_dte_max": 90,
    "exit_dte": 7,
    "dte_interval": 7,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
    # Slippage settings
    "slippage": "mid",  # "mid", "spread", or "liquidity"
    "fill_ratio": 0.5,  # Base fill ratio for liquidity mode (0.0-1.0)
    "reference_volume": 1000,  # Volume threshold for liquid options
}


class Side(Enum):
    """Enum representing long or short position side with multiplier values."""

    long = 1
    short = -1


def _singles(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
    """Process single-leg option strategies (calls or puts)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=single_strike_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=leg_def,
        params=params,
    )


def _straddles(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
    """Process straddle strategies (call and put at same strike)."""
    params = {**default_kwargs, **kwargs}

    return _process_strategy(
        data,
        internal_cols=straddle_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=leg_def,
        join_on=[
            "underlying_symbol",
            "expiration",
            "strike",
            "dte_entry",
            "dte_range",
            "otm_pct_range",
            "underlying_price_entry",
        ],
        params=params,
    )


def _strangles(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
    """Process strangle strategies (call and put at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def _spread(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
    """Process vertical spread strategies (call or put spreads at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def long_calls(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long call strategy statistics.

    The classic bullish bet.  Buying a call gives you the right to purchase
    shares at the strike price, offering leveraged upside without the full
    cost of owning stock.  Your risk is capped at the premium paid, but
    your upside is theoretically unlimited.  Think of it as paying a small
    admission fee to ride the rally.

    Payoff at expiration::

        P&L
         |            /
         |           /
         |          /
        -|--------+-------> Price
         |  (loss capped
         |   at premium)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters (dte_interval, max_entry_dte, etc.)

    Returns:
        DataFrame with long call strategy performance statistics.
    """
    return _singles(data, [(Side.long, _calls)], **kwargs)


def long_puts(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long put strategy statistics.

    The bearish bet and the market's favourite insurance policy.  Buying a
    put gives you the right to sell shares at the strike price, so you
    profit when the underlying drops.  Portfolio managers use these like
    homeowner's insurance — you hope you never need it, but you sleep
    better knowing it's there.

    Payoff at expiration::

        P&L
         \\
          \\
           \\
        ----+---------> Price
              (loss capped
               at premium)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long put strategy performance statistics.
    """
    return _singles(data, [(Side.long, _puts)], **kwargs)


def short_calls(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short call strategy statistics.

    The income play for the mildly bearish (or at least not-very-bullish).
    You sell a call and collect premium upfront, betting the stock won't
    rally past the strike.  Time decay is your best friend here — every
    day that passes with the stock sitting still puts money in your pocket.
    But beware: if the stock rockets higher, your losses are unlimited.

    Payoff at expiration::

        P&L
         |  (profit capped
         |   at premium)
        -|--------+-------> Price
         |         \\
         |          \\

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short call strategy performance statistics.
    """
    return _singles(data, [(Side.short, _calls)], **kwargs)


def short_puts(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short put strategy statistics.

    The "I'd love to buy that stock cheaper" play.  You sell a put and
    collect premium, essentially getting paid to wait for a dip.  If
    the stock stays above the strike you keep the premium; if it drops
    below, you're obligated to buy at the strike — which you wanted to
    do anyway.  Warren Buffett's favourite options strategy.

    Payoff at expiration::

        P&L
              (profit capped
               at premium)
        ----+---------> Price
           /
          /

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short put strategy performance statistics.
    """
    return _singles(data, [(Side.short, _puts)], **kwargs)


def long_straddles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long straddle strategy statistics.

    The "something big is about to happen" play.  You buy both a call and
    a put at the same strike, so you profit from a large move in *either*
    direction.  Earnings announcements, FDA decisions, election nights —
    any event where you expect fireworks but don't know which way the
    sparks will fly.  The catch: you're paying double premium, so the
    move needs to be big enough to cover both tickets.

    Structure: long call + long put at the same strike.

    Payoff at expiration::

        P&L
         \\          /
          \\        /
           \\      /
        ----+----+----> Price
             strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long straddle strategy performance statistics.
    """
    return _straddles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_straddles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short straddle strategy statistics.

    The "absolutely nothing is going to happen" play.  You sell both a
    call and a put at the same strike, collecting double premium and
    betting the stock goes nowhere.  Maximum profit if the underlying
    pins the strike at expiration.  Popular in low-volatility
    environments, but dangerous around catalysts — losses are unlimited
    in both directions.

    Structure: short call + short put at the same strike.

    Payoff at expiration::

        P&L
        ----+----+----> Price
           /      \\
          /        \\
         /          \\
             strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short straddle strategy performance statistics.
    """
    return _straddles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_strangles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long strangle strategy statistics.

    The straddle's budget-friendly cousin.  You buy a call and a put at
    *different* strikes (both OTM), so the upfront cost is cheaper than
    a straddle.  The trade-off: the stock needs to move even further to
    turn a profit, since it has to blow past one of the two strikes.
    Great for when you expect a monster move but want to spend less on
    the setup.

    Structure: long put (lower strike) + long call (higher strike).

    Payoff at expiration::

        P&L
         \\            /
          \\          /
           +--------+----> Price
           put     call

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long strangle strategy performance statistics.
    """
    return _strangles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_strangles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short strangle strategy statistics.

    The short straddle with a wider safety net.  You sell an OTM put and
    an OTM call, collecting less premium than a straddle but giving
    yourself a comfortable range where the stock can wander without
    hurting you.  A favourite of income-oriented traders who want to
    sell volatility with some breathing room.

    Structure: short put (lower strike) + short call (higher strike).

    Payoff at expiration::

        P&L
           +--------+----> Price
          /          \\
         /            \\
           put     call

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short strangle strategy performance statistics.
    """
    return _strangles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_call_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long call spread (bull call spread) statistics.

    The budget bull.  You buy a lower-strike call and sell a higher-strike
    call, cutting your cost (and capping your upside) compared to a naked
    long call.  Both profit and loss are bounded, making this a
    controlled-risk way to bet on a moderate rally.  It's the training
    wheels of bullish options plays — responsible, defined-risk, and
    surprisingly effective.

    Structure: long call (lower strike) + short call (higher strike).

    Payoff at expiration::

        P&L
         |       +------  max profit
         |      /
         |     /
        -|----+----------> Price
         |  max loss

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long call spread strategy performance statistics.
    """
    return _spread(data, [(Side.long, _calls), (Side.short, _calls)], **kwargs)


def short_call_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short call spread (bear call spread) statistics.

    The mildly bearish income play.  You sell a lower-strike call and
    buy a higher-strike call for protection, collecting a net credit.
    You keep the full premium if the stock stays below the short strike.
    Think of it as saying "I don't think this stock is going anywhere
    exciting" and getting paid for that opinion.

    Structure: short call (lower strike) + long call (higher strike).

    Payoff at expiration::

        P&L
         |  max profit
        -|----+----------> Price
         |     \\
         |      \\
         |       +------  max loss

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short call spread strategy performance statistics.
    """
    return _spread(data, [(Side.short, _calls), (Side.long, _calls)], **kwargs)


def long_put_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long put spread (bear put spread) statistics.

    The budget bear.  You buy a higher-strike put and sell a lower-strike
    put, reducing your cost compared to a naked long put but capping how
    much you can make on the way down.  Both risk and reward are neatly
    defined — you know your worst-case scenario before you even place the
    trade.  The go-to play for a measured bearish outlook.

    Structure: short put (lower strike) + long put (higher strike).

    Payoff at expiration::

        P&L
         |  max profit
        -|--------+-------> Price
         |       /
         |      /
         |     +---  max loss

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long put spread strategy performance statistics.
    """
    return _spread(data, [(Side.short, _puts), (Side.long, _puts)], **kwargs)


def short_put_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short put spread (bull put spread) statistics.

    The mildly bullish income play.  You sell a higher-strike put and
    buy a lower-strike put for protection, pocketing a net credit.
    As long as the stock stays above the short strike, you walk away
    with the premium.  It's the put-side mirror of a bear call spread
    and a popular choice for traders who want to sell premium with a
    built-in safety harness.

    Structure: long put (lower strike) + short put (higher strike).

    Payoff at expiration::

        P&L
         |       +------  max profit
         |      /
         |     /
        -|----+----------> Price
         |  max loss

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short put spread strategy performance statistics.
    """
    return _spread(data, [(Side.long, _puts), (Side.short, _puts)], **kwargs)


# =============================================================================
# Butterfly Strategies (3 legs)
# =============================================================================


def _butterfly(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
    """Process butterfly strategies (3 legs at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=triple_strike_internal_cols,
        external_cols=triple_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_butterfly_strikes,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def long_call_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long call butterfly strategy statistics.

    The sniper of options strategies.  You're targeting a very specific
    price at expiration — the middle strike — and if you nail it, the
    reward-to-risk ratio is excellent.  The trade costs very little to
    enter (the wings finance each other), but the profit zone is narrow.
    Often used by traders who have a strong conviction on *where* a stock
    will land, not just *which direction* it will go.

    Structure:
        - Long 1 call at lower strike (wing)
        - Short 2 calls at middle strike (body)
        - Long 1 call at upper strike (wing)

    Payoff at expiration::

        P&L
         |       /\\
         |      /  \\
         |     /    \\
        -|----+------+---> Price
         |  wing  body  wing

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long call butterfly strategy performance statistics.
    """
    return _butterfly(
        data,
        [
            (Side.long, _calls, 1),
            (Side.short, _calls, 2),
            (Side.long, _calls, 1),
        ],
        **kwargs,
    )


def short_call_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short call butterfly strategy statistics.

    The anti-sniper.  While the long butterfly bets on precision, this
    trade bets on chaos.  You collect a small credit and profit whenever
    the stock moves far enough away from the middle strike in either
    direction.  Your max loss is small and occurs only if the stock lands
    right on the body at expiration — the exact sweet spot your opponent
    is aiming for.

    Structure:
        - Short 1 call at lower strike (wing)
        - Long 2 calls at middle strike (body)
        - Short 1 call at upper strike (wing)

    Payoff at expiration::

        P&L
        -|----+------+---> Price
         |     \\    /
         |      \\  /
         |       \\/

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short call butterfly strategy performance statistics.
    """
    return _butterfly(
        data,
        [
            (Side.short, _calls, 1),
            (Side.long, _calls, 2),
            (Side.short, _calls, 1),
        ],
        **kwargs,
    )


def long_put_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long put butterfly strategy statistics.

    Same pinpoint precision as the long call butterfly, built with puts
    instead.  The payoff profile is identical — you're still betting the
    stock lands near the middle strike — but using puts can sometimes
    offer slightly different pricing due to put-call skew.  Experienced
    traders compare both versions and pick whichever is cheaper to enter.

    Structure:
        - Long 1 put at lower strike (wing)
        - Short 2 puts at middle strike (body)
        - Long 1 put at upper strike (wing)

    Payoff at expiration::

        P&L
         |       /\\
         |      /  \\
         |     /    \\
        -|----+------+---> Price
         |  wing  body  wing

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long put butterfly strategy performance statistics.
    """
    return _butterfly(
        data,
        [
            (Side.long, _puts, 1),
            (Side.short, _puts, 2),
            (Side.long, _puts, 1),
        ],
        **kwargs,
    )


def short_put_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short put butterfly strategy statistics.

    The put-side anti-sniper.  You collect a small credit and profit when
    the stock moves decisively away from the middle strike.  Like all
    short butterflies, this is a bet on movement and volatility rather
    than a specific price target.

    Structure:
        - Short 1 put at lower strike (wing)
        - Long 2 puts at middle strike (body)
        - Short 1 put at upper strike (wing)

    Payoff at expiration::

        P&L
        -|----+------+---> Price
         |     \\    /
         |      \\  /
         |       \\/

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short put butterfly strategy performance statistics.
    """
    return _butterfly(
        data,
        [
            (Side.short, _puts, 1),
            (Side.long, _puts, 2),
            (Side.short, _puts, 1),
        ],
        **kwargs,
    )


# =============================================================================
# Iron Condor and Iron Butterfly Strategies (4 legs)
# =============================================================================


def _iron_condor(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any
) -> pd.DataFrame:
    """Process iron condor strategies (4 legs at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=quadruple_strike_internal_cols,
        external_cols=quadruple_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_iron_condor_strikes,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def _iron_butterfly(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any
) -> pd.DataFrame:
    """Process iron butterfly strategies (4 legs, middle legs share strike)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=quadruple_strike_internal_cols,
        external_cols=quadruple_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_iron_butterfly_strikes,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def iron_condor(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate iron condor strategy statistics.

    The range-bound income machine and one of the most popular premium-
    selling strategies.  You define a corridor with two short strikes and
    protect each side with a long wing.  As long as the stock stays
    inside the corridor, you keep the credit.  Think of it as building a
    fence around the stock and collecting rent — the wider the fence, the
    less rent, but the safer you sleep.

    Structure:
        - Long 1 put at lowest strike (protection)
        - Short 1 put at lower-middle strike (income)
        - Short 1 call at upper-middle strike (income)
        - Long 1 call at highest strike (protection)

    Payoff at expiration::

        P&L
         |     +--------+
         |    /          \\
        -|---+            +---> Price
         | wing  profit   wing
         |       zone

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with iron condor strategy performance statistics.
    """
    return _iron_condor(
        data,
        [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ],
        **kwargs,
    )


def reverse_iron_condor(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate reverse iron condor strategy statistics.

    The breakout bet.  This is the iron condor flipped on its head — you
    *pay* a small debit and profit when the stock bursts out of its range
    in either direction.  Useful ahead of binary events when implied
    volatility hasn't fully priced in the potential move.  Your max loss
    is the small debit paid if the stock stays stubbornly in the middle.

    Structure:
        - Short 1 put at lowest strike
        - Long 1 put at lower-middle strike
        - Long 1 call at upper-middle strike
        - Short 1 call at highest strike

    Payoff at expiration::

        P&L
        -|---+            +---> Price
         |    \\          /
         |     +--------+
         |       loss
         |       zone

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with reverse iron condor strategy performance statistics.
    """
    return _iron_condor(
        data,
        [
            (Side.short, _puts),
            (Side.long, _puts),
            (Side.long, _calls),
            (Side.short, _calls),
        ],
        **kwargs,
    )


def iron_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate iron butterfly strategy statistics.

    The iron condor's sharper-edged sibling.  By collapsing the two
    short strikes into a single ATM strike, you collect a much larger
    credit but give yourself a much narrower profit zone.  Maximum
    profit happens when the stock expires exactly at that middle
    strike — so this is really a premium-seller's precision play.
    Higher reward, higher risk, zero room for wandering.

    Structure:
        - Long 1 put at lowest strike (wing)
        - Short 1 put at middle strike (body)
        - Short 1 call at middle strike (body) — same strike as short put
        - Long 1 call at highest strike (wing)

    Payoff at expiration::

        P&L
         |       /\\
         |      /  \\
         |     /    \\
        -|----+------+---> Price
         |  wing  body  wing

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with iron butterfly strategy performance statistics.
    """
    return _iron_butterfly(
        data,
        [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ],
        **kwargs,
    )


def reverse_iron_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate reverse iron butterfly strategy statistics.

    The precision breakout play.  You buy an ATM straddle (the body) and
    sell the wings for protection, paying a small net debit.  Profits
    grow as the stock moves away from the middle strike in either
    direction, capped at the wing width.  A defined-risk alternative
    to a long straddle when you want cheaper exposure to a big move.

    Structure:
        - Short 1 put at lowest strike (wing)
        - Long 1 put at middle strike (body)
        - Long 1 call at middle strike (body) — same strike as long put
        - Short 1 call at highest strike (wing)

    Payoff at expiration::

        P&L
        -|----+------+---> Price
         |     \\    /
         |      \\  /
         |       \\/

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with reverse iron butterfly strategy performance statistics.
    """
    return _iron_butterfly(
        data,
        [
            (Side.short, _puts),
            (Side.long, _puts),
            (Side.long, _calls),
            (Side.short, _calls),
        ],
        **kwargs,
    )


# =============================================================================
# Covered Strategies
# =============================================================================


def _covered_call(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any
) -> pd.DataFrame:
    """
    Process covered call strategy.

    Note: This implementation simulates a covered call using options data only,
    approximating the underlying position through the relationship between
    option premiums and underlying price changes.
    """
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def covered_call(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate covered call strategy statistics.

    The landlord of options strategies.  You own the stock (simulated here
    via a deep ITM call) and sell someone else the right to buy it from
    you at a higher price.  You collect rent (premium) every month and
    keep your upside up to the short strike.  If the stock gets called
    away, you've sold at a price you were happy with.  The most popular
    options strategy in the world — and for good reason.

    Structure:
        - Long underlying position (simulated via long deep ITM call)
        - Short 1 call at higher strike

    Note: This implementation uses a synthetic approach with options only.

    Payoff at expiration::

        P&L
         |        +------  capped upside
         |       /
         |      /
        -|-----+---------> Price
         | (downside risk)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with covered call strategy performance statistics.
    """
    return _covered_call(
        data,
        [
            (Side.long, _calls),
            (Side.short, _calls),
        ],
        **kwargs,
    )


def protective_put(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate protective put (married put) strategy statistics.

    Portfolio insurance.  You own the stock (simulated via a deep ITM call)
    and buy a put to protect against a crash.  Your upside is unlimited,
    and your downside is floored at the put strike.  The premium you pay
    is the cost of sleeping peacefully through earnings season, geopolitical
    chaos, or whatever the market throws at you.

    Structure:
        - Long underlying position (simulated via long deep ITM call)
        - Long 1 put at lower strike for protection

    Note: This implementation uses a synthetic approach with options only.

    Payoff at expiration::

        P&L
         |            /
         |           /
         |          /
        -|----+---+-------> Price
         |    | floor
         |    +---  (loss capped by put)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with protective put strategy performance statistics.
    """
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=[
            (Side.long, _calls),
            (Side.long, _puts),
        ],
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


# =============================================================================
# Calendar and Diagonal Spread Strategies
# =============================================================================


def _calendar_spread(
    data: pd.DataFrame, leg_def: List[Tuple], same_strike: bool = True, **kwargs: Any
) -> pd.DataFrame:
    """
    Process calendar or diagonal spread strategies.

    Calendar spreads have the same strike but different expirations.
    Diagonal spreads have different strikes and different expirations.

    Args:
        data: DataFrame containing option chain data
        leg_def: List of tuples defining strategy legs [(side, option_filter), ...]
        same_strike: True for calendar spreads, False for diagonal spreads
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with calendar/diagonal spread strategy results
    """
    params = {**calendar_default_kwargs, **kwargs}
    internal_cols = (
        calendar_spread_internal_cols if same_strike else diagonal_spread_internal_cols
    )
    external_cols = (
        calendar_spread_external_cols if same_strike else diagonal_spread_external_cols
    )

    return _process_calendar_strategy(
        data,
        internal_cols=internal_cols,
        external_cols=external_cols,
        leg_def=leg_def,
        rules=_rule_expiration_ordering,
        same_strike=same_strike,
        params=params,
    )


def long_call_calendar(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long call calendar spread strategy statistics.

    The time-decay harvester.  You sell a short-dated call and buy a
    longer-dated call at the same strike.  Because the front-month
    option decays faster (theta accelerates near expiration), the spread
    widens in your favour as time passes — as long as the stock cooperates
    and stays near the strike.  A favourite in low-volatility environments
    when you expect the stock to drift sideways for a while.

    Structure:
        - Short 1 front-month call (near-term expiration)
        - Long 1 back-month call (longer-term expiration)
        - Both at the same strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters including:

            - front_dte_min: Minimum DTE for front leg (default: 20).
            - front_dte_max: Maximum DTE for front leg (default: 40).
            - back_dte_min: Minimum DTE for back leg (default: 50).
            - back_dte_max: Maximum DTE for back leg (default: 90).
            - exit_dte: Days before front expiration to exit (default: 7).

    Returns:
        DataFrame with long call calendar spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.short, _calls), (Side.long, _calls)], same_strike=True, **kwargs
    )


def short_call_calendar(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short call calendar spread strategy statistics.

    The anti-calendar.  You flip the usual time-decay trade on its head:
    buy the fast-decaying front month and sell the slow-decaying back
    month.  You profit when the stock makes a big move (either direction)
    that destroys the back-month's time value, or when implied volatility
    collapses.  A contrarian play that bets against sideways markets.

    Structure:
        - Long 1 front-month call (near-term expiration)
        - Short 1 back-month call (longer-term expiration)
        - Both at the same strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short call calendar spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.long, _calls), (Side.short, _calls)], same_strike=True, **kwargs
    )


def long_put_calendar(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long put calendar spread strategy statistics.

    The put-side time-decay harvester.  Same concept as the call calendar
    — profit from the front month decaying faster than the back month —
    but built with puts.  Particularly useful when put skew makes this
    version cheaper than its call counterpart, or when you want a
    slightly bearish tilt to your neutral position.

    Structure:
        - Short 1 front-month put (near-term expiration)
        - Long 1 back-month put (longer-term expiration)
        - Both at the same strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long put calendar spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.short, _puts), (Side.long, _puts)], same_strike=True, **kwargs
    )


def short_put_calendar(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short put calendar spread strategy statistics.

    The put-side anti-calendar.  Same contrarian logic as the short call
    calendar — you're betting against a quiet market — but expressed
    through puts.  Profits from a large move in the underlying or a
    collapse in implied volatility.

    Structure:
        - Long 1 front-month put (near-term expiration)
        - Short 1 back-month put (longer-term expiration)
        - Both at the same strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short put calendar spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.long, _puts), (Side.short, _puts)], same_strike=True, **kwargs
    )


def long_call_diagonal(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long call diagonal spread strategy statistics.

    The versatile hybrid.  A diagonal combines the time-decay benefits
    of a calendar spread with the directional tilt of a vertical spread.
    You sell a short-dated call and buy a longer-dated call at a
    *different* strike.  By choosing different strikes you can skew the
    trade bullish (buy a lower strike) or neutral (buy a higher strike).
    One of the most flexible structures in the options playbook.

    Structure:
        - Short 1 front-month call (near-term expiration)
        - Long 1 back-month call (longer-term expiration)
        - Different strikes for each leg

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long call diagonal spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.short, _calls), (Side.long, _calls)], same_strike=False, **kwargs
    )


def short_call_diagonal(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short call diagonal spread strategy statistics.

    The reverse diagonal.  You buy the front month and sell the back
    month at different strikes, profiting when the stock moves sharply
    or when implied volatility drops.  The strike difference adds a
    directional component to the volatility bet, making this a nuanced
    tool for traders with a view on both direction and vol.

    Structure:
        - Long 1 front-month call (near-term expiration)
        - Short 1 back-month call (longer-term expiration)
        - Different strikes for each leg

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short call diagonal spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.long, _calls), (Side.short, _calls)], same_strike=False, **kwargs
    )


def long_put_diagonal(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long put diagonal spread strategy statistics.

    The put-side hybrid.  Sell a short-dated put and buy a longer-dated
    put at a different strike to combine time-decay income with a
    bearish (or neutral) directional view.  The flexibility of choosing
    different strikes makes this popular with traders who want to fine-tune
    their exposure rather than just going "bullish" or "bearish."

    Structure:
        - Short 1 front-month put (near-term expiration)
        - Long 1 back-month put (longer-term expiration)
        - Different strikes for each leg

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long put diagonal spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.short, _puts), (Side.long, _puts)], same_strike=False, **kwargs
    )


def short_put_diagonal(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short put diagonal spread strategy statistics.

    The put-side reverse diagonal.  Buy the front month put and sell the
    back month put at different strikes, creating a position that profits
    from movement and volatility compression.  The strike difference lets
    you dial in a bearish or neutral bias on top of the volatility trade.

    Structure:
        - Long 1 front-month put (near-term expiration)
        - Short 1 back-month put (longer-term expiration)
        - Different strikes for each leg

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short put diagonal spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.long, _puts), (Side.short, _puts)], same_strike=False, **kwargs
    )
