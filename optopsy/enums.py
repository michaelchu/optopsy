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
    
class Struct(Enum):
	CBOE = (
    	('symbol', 0),
    	('quote_date', 1),
    	('root', 2),
    	('expiration', 3),
    	('strike', 4),
    	('option_type', 5),
    	('bid', 12),
    	('ask', 14),
    	('underlying_price', 17),
    	('delta', 19),
    	('gamma', 20),
    	('theta', 21),
    	('vega', 22)
	)


class OptionType(Enum):
    CALL = ('c', 1)
    PUT = ('p', -1)


class OrderAction(Enum):
    BTO = (1, 'BUY', 'BOT')
    BTC = (1, 'BUY', 'BOT')
    STO = (-1, 'SELL', 'SLD')
    STC = (-1, 'SELL', 'SLD')


class DayOfWeek(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

