[![Downloads](https://pepy.tech/badge/optopsy)](https://pepy.tech/project/optopsy)
[![Maintainability](https://api.codeclimate.com/v1/badges/37b11e992a6900d30310/maintainability)](https://codeclimate.com/github/michaelchu/optopsy/maintainability)
[![Build Status](https://travis-ci.org/michaelchu/optopsy.svg?branch=master)](https://travis-ci.org/michaelchu/optopsy)
[![Test Coverage](https://api.codeclimate.com/v1/badges/37b11e992a6900d30310/test_coverage)](https://codeclimate.com/github/michaelchu/optopsy/test_coverage)

# Optopsy

Optopsy is a flexible backtesting framework used to test complex options trading strategies written in Python.
Backtesting is the process of testing a strategy over a given data set. This framework allows you to mix and match
different 'filters' to create a 'Strategy', and allow multiple strategies to form an overall more complex trading algorithms.
The modular nature of this framework aims to foster the creation of easily testable, re-usable and flexible blocks of strategy logic to facilitate
the rapid development of complex options trading strategies.

## Features

### Easy Backtesting
* Easily set up a backtest in seconds by defining filters for the backtest

### Use Your Data
* Use data from any source, just define the format of your data source or use pre-existing data structs for popular sources such as CBOE and Historical Options Data.

### Advanced Backtest Parameters:

**Entry rules:**
* Days to expiration
* Entry Days (Staggered trades)
* Absolute Delta
* Percentage out-of-the-money
* Contract size

**Exit rules:**
* Days to expiration
* Hold days
* Profit/Stop loss percent
* Spread delta
* Spread price

### Option strategy support
* Single Calls/Puts
* Vertical Spreads
* Iron Condors
* (Coming Soon) Iron Butterfly
* (Coming Soon) Covered Stock
* (Coming Soon) Combos (Synthetics/Collars)
* (Coming Soon) Diagonal Spreads
* (Coming Soon) Calendar Spreads
* (Coming Soon) Custom Spreads
* (Coming Soon) Strangles
* (Coming Soon) Straddles

### Dependencies
You will need Python 3.6.x and Pandas 0.23.1 or newer. It is recommended to install [Miniconda3](https://conda.io/miniconda.html). See [requirements.txt](https://github.com/michaelchu/optopsy/blob/master/requirements.txt) for full details.

### Installation
```
pip install optopsy
```

### Usage
```
python strategies/sample_strategy.py
```
The sample strategy can be used with [Level 2 Historical CSV Data Sample](http://www.deltaneutral.com/files/Sample_SPX_20151001_to_20151030.csv) from historicaloptiondata.com.

In order to use it, you will need to define the struct variable to map the column names to the numerical index as per the file format.

First we import the library and other nessesary libaries:
```python
import optopsy as op
from datetime import datetime
```

Define the data structure with a tuple of tuple format, with first element being the standard column names defined in optopsy and the index that corresponds to the column order of the input source
```python
SPX_FILE_STRUCT = (
    ('underlying_symbol', 0),
    ('underlying_price', 1),
    ('option_symbol', 3),
    ('option_type', 5),
    ('expiration', 6),
    ('quote_date', 7),
    ('strike', 8),
    ('bid', 10),
    ('ask', 11),
    ('delta', 15),
    ('gamma', 16),
    ('theta', 17),
    ('vega', 18)
)
```

An example of a simple strategy for trading short call spreads with strikes at 30 and 50 deltas with around 30 days to expiration for the SPX:
```python
def run_strategy():

    # provide the absolute file path and data struct to be used.
    data = op.get(FILE, SPX_FILE_STRUCT, prompt=False)

    # define the entry and exit filters to use for this strategy, full list of
    # filters is listed in the documentation (WIP).
    filters = {
        'entry_dte': (27, 30, 31),
        'leg1_delta': 0.30,
        'leg2_delta': 0.50,
        'contract_size': 10
    }

    # set the start and end dates for the backtest, the dates are inclusive
    start = datetime(2016, 1, 1)
    end = datetime(2016, 12, 31)

    # create the option spreads that matches the entry filters
    trades = op.strategies.short_call_spread(data, start, end, filters)

    # call the run method with our data, option spreads and filters to run the backtest
    backtest = op.run(data, trades, filters)

    # backtest will return a tuple with the profit amount (first element) and a dataframe
    # (second element) containing the backtest results(the return format may be subject to change)
    backtest[1].to_csv('./strategies/results/results.csv')
    print("Total Profit: %s" % backtest[0])
```

#### Sample Backtest Results:


Entry Trades (First 2 trades):

```
quote_date option_type expiration underlying_symbol  ratio  delta  underlying_price        option_symbol  strike   bid   ask  gamma   theta    vega  dte  contracts
2016-01-06           c 2016-02-05              SPXW     -1   0.50           1987.42  SPXW160205C01990000    1990  42.1  42.8    0.0 -274.85  224.75   30         10
2016-01-06           c 2016-02-05              SPXW      1   0.30           1987.42  SPXW160205C02040000    2040  17.4  17.8    0.0 -208.37  196.71   30         10
2016-01-13           c 2016-02-12              SPXW     -1   0.51           1891.49  SPXW160212C01885000    1885  49.8  50.8    0.0 -202.50  213.03   30         10
2016-01-13           c 2016-02-12              SPXW      1   0.30           1891.49  SPXW160212C01940000    1940  22.4  23.0    0.0 -187.45  185.48   30         10
...
```

Results (First 2 trades):
```
entry_date  exit_date expiration  DTE  ratio  contracts option_type  strike  entry_delta  entry_stk_price  exit_stk_price  entry_opt_price  exit_opt_price  entry_price  exit_price  profit
2016-01-06 2016-02-05 2016-02-05   30     -1         10           c    1990         0.50          1987.42         1874.12            42.45           0.025       -424.5       -0.25  424.25
2016-01-06 2016-02-05 2016-02-05   30      1         10           c    2040         0.30          1987.42         1874.12            17.60           0.025        176.0        0.25 -175.75
2016-01-13 2016-02-12 2016-02-12   30     -1         10           c    1885         0.51          1891.49         1862.40            50.30           0.025       -503.0       -0.25  502.75
2016-01-13 2016-02-12 2016-02-12   30      1         10           c    1940         0.30          1891.49         1862.40            22.70           0.025        227.0        0.25 -226.75
...

Total Profit: 524.50
```

**Full Documentation Coming Soon!**