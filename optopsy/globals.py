from enum import Enum

class Period(Enum):
    DAY = 1
    TWO_DAYS = 2
    THREE_DAYS = 3
    FOUR_DAYS = 4
    FIVE_DAYS = 5
    SIX_DAYS = 6
    ONE_WEEK = 7
    TWO_WEEKS = 14
    THREE_WEEKS = 21
    FOUR_WEEKS = 28
    FIVE_WEEKS = 35
    SIX_WEEKS = 42
    SEVEN_WEEKS = 49


class OptionType(Enum):
    CALL = ('c', 1)
    PUT = ('p', -1)


class OrderAction(Enum):
    BTO = (1, 'BUY', 'BOT')
    BTC = (1, 'BUY', 'BOT')
    STO = (-1, 'SELL', 'SLD')
    STC = (-1, 'SELL', 'SLD')


class OptionStrategy(Enum):
    SINGLE = "single"
    VERTICAL = "vertical"
    IRON_CONDOR = "iron_condor"
    COVERED_STOCK = "covered_stock"
    DIAGONAL = "diagonal"
    DOUBLE_DIAGONAL = "double_diagonal"
    CALENDAR = "calendar"
    STRADDLE = "straddle"
    COMBO = "combo"
    BACK_RATIO = "back_ratio"
    BUTTERFLY = "butterfly"
    CONDOR = "condor"


class DayOfWeek(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


OrderType = Enum("OrderType", "MKT, LMT, STPLMT")
SecType = Enum("SecType", "STK, OPT")
OrderStatus = Enum("OrderStatus", "WORKING, REJECTED, FILLED, DELETED, EXPIRED")
OrderTIF = Enum("OrderTIF", "GTC, DAY")