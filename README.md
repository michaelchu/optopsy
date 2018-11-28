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
git clone git@github.com:michaelchu/optopsy.git
cd optopsy
python3 -m pip install --user virtualenv
python3 -m virtualenv env
source env/bin/activate
pip install optopsy
pip install -r requirements.txt
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

Define the data structure of your input file with a tuple of tuple format, with first element being the standard column names defined in optopsy and the second elmemnt being the index that corresponds to the column order of the input source. (The indices are 0-indexed)
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
import os
from datetime import datetime
import pandas as pd
import optopsy as op


def run_strategy(data):
    # define the entry and exit filters to use for this strategy, full list of
    # filters will be listed in the documentation (WIP).
    filters = {
         # dates are inclusive and are datetime objects
        "start_date": datetime(2016, 1, 1),
        "end_date": datetime(2018, 2, 28),
        # values can be a tuple where first element: min value, 
        # second element: ideal (nearest) to this value, third element: max value
        "entry_dte": (6, 7, 8),
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
        "contract_size": 1,
        # Select only standard options
        "expr_type": ["SPX"],
    }

    # set the start and end dates for the backtest, the dates are inclusive,
    # start and end dates are python datetime objects.
    # strategy functions will return a dataframe containing all the simulated trades
    return op.long_call_spread(data, filters)


def store_and_get_data(file_name):
    # absolute file path to our input file
    curr_file = os.path.abspath(os.path.dirname(__file__))
    file = os.path.join(curr_file, "data", f"{file_name}.pkl")

    # check if we have a pickle store
    if os.path.isfile(file):
        print("pickle file found, retrieving...")
        return pd.read_pickle(file)
    else:
        print("no picked file found, retrieving csv data...")

        csv_file = os.path.join(curr_file, "data", f"{file_name}.csv")
        data = op.get(csv_file, SPX_FILE_STRUCT, prompt=False)

        print("storing to pickle file...")
        pd.to_pickle(data, file)
        return data


if __name__ == "__main__":
    # Here we define the struct to match the format of our csv file
    # the struct indices are 0-indexed where first column of the csv file
    # is mapped to 0
    SPX_FILE_STRUCT = (
        ("underlying_symbol", 0),
        ("underlying_price", 1),
        ("option_type", 5),
        ("expiration", 6),
        ("quote_date", 7),
        ("strike", 8),
        ("bid", 10),
        ("ask", 11),
        ("delta", 15),
        ("gamma", 16),
        ("theta", 17),
        ("vega", 18),
    )

    # calling results function from the results returned from run_strategy()
    r = store_and_get_data("SPX_2018").pipe(run_strategy).pipe(op.results)

    # the first item in tuple returned from op.results is the sumamary stats
    print(r[0])

    # second item is a dataframe containing all the trades of the strategy
    print(r[1])
```

#### Sample Backtest Results:

Results:
```
{
    'Initial Balance': 10000, 
    'Ending Balance': 8560.0, 
    'Total Profit': -1440.0, 
    'Total Win Count': 0, 
    'Total Win Percent': 0.0, 
    'Total Loss Count': 2, 
    'Total Loss Percent': 1.0, 
    'Total Trades': 2
}
```

Trades:
```
          entry_date  exit_date expiration underlying_symbol  dte  ratio  contracts option_type  strike  entry_delta  entry_stk_price  exit_stk_price  entry_opt_price  exit_opt_price  entry_price  exit_price    cost
trade_num
0         2018-01-24 2018-01-31 2018-01-31              SPXW    7      1          1           c    2840         0.48          2837.60         2823.89             15.0           -0.00       1500.0        -0.0  1500.0
0         2018-01-24 2018-01-31 2018-01-31              SPXW    7     -1          1           c    2860         0.28          2837.60         2823.89             -6.4            0.05       -640.0         5.0  -635.0
1         2018-02-21 2018-02-28 2018-02-28              SPXW    7      1          1           c    2705         0.48          2701.39         2713.78             20.7           -5.80       2070.0      -580.0  1490.0
1         2018-02-21 2018-02-28 2018-02-28              SPXW    7     -1          1           c    2730         0.30          2701.39         2713.78             -9.2            0.05       -920.0         5.0  -915.0
...

Total Profit: -1440.0
```

**Full Documentation Coming Soon!**