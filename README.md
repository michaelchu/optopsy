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
        "start_date": datetime(2016, 1, 1), # dates are inclusive and are datetime objects
        "end_date": datetime(2016, 12, 31),
        # values can be tupples where first element: min value, 
        # second element: ideal (nearest) to this value, third element: max value
        "entry_dte": (27, 30, 31), 
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
        "contract_size": 10,
        "expr_type": ["SPX"], # select only weekly options
    }


    # strategy functions will return a dataframe containing all the simulated trades
    return op.long_call_spread(data, filters)


def store_and_get_data(file_name):
    # absolute file path to our input file
    curr_file = os.path.abspath(os.path.dirname(__file__))
    file = os.path.join(curr_file, "data", f"{file_name}.pkl")

    # check if we have a pickle store, if exists, use it, otherwise create it 
    # to save time on subsequent runs
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
        ("option_symbol", 3),
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
    r = store_and_get_data("SPX_2016").pipe(run_strategy).pipe(op.results)

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
    'Ending Balance': 49100.0, 
    'Total Profit': 39100.0, 
    'Total Win Count': 7, 
    'Total Win Percent': 0.64, 
    'Total Loss Count': 4, 
    'Total Loss Percent': 0.36, 
    'Total Trades': 11
}
```

Trades:
```
          entry_date  exit_date expiration underlying_symbol  dte  ratio  contracts option_type  strike  entry_delta  entry_stk_price  exit_stk_price  entry_opt_price  exit_opt_price  entry_price  exit_price     cost
trade_num
0         2016-01-20 2016-02-19 2016-02-19               SPX   30      1         10           c    1865         0.49          1864.38         1917.01             45.8          -51.30      45800.0    -51300.0  -5500.0
0         2016-01-20 2016-02-19 2016-02-19               SPX   30     -1         10           c    1920         0.29          1864.38         1917.01            -18.4            7.20     -18400.0      7200.0 -11200.0
1         2016-02-17 2016-03-18 2016-03-18               SPX   30      1         10           c    1925         0.50          1926.46         2049.39             43.5         -114.30      43500.0   -114300.0 -70800.0
1         2016-02-17 2016-03-18 2016-03-18               SPX   30     -1         10           c    1980         0.29          1926.46         2049.39            -16.2           60.80     -16200.0     60800.0  44600.0
2         2016-03-16 2016-04-15 2016-04-15               SPX   30      1         10           c    2025         0.51          2028.07         2079.46             30.2          -54.90      30200.0    -54900.0 -24700.0
2         2016-03-16 2016-04-15 2016-04-15               SPX   30     -1         10           c    2060         0.31          2028.07         2079.46            -12.2           27.50     -12200.0     27500.0  15300.0
3         2016-04-20 2016-05-20 2016-05-20               SPX   30      1         10           c    2100         0.51          2103.27         2051.32             27.4           -0.00      27400.0        -0.0  27400.0
3         2016-04-20 2016-05-20 2016-05-20               SPX   30     -1         10           c    2130         0.31          2103.27         2051.32            -11.5            0.05     -11500.0        50.0 -11450.0
4         2016-05-18 2016-06-17 2016-06-17               SPX   30      1         10           c    2045         0.49          2043.22         2070.97             31.5          -31.40      31500.0    -31400.0    100.0
4         2016-05-18 2016-06-17 2016-06-17               SPX   30     -1         10           c    2080         0.31          2043.22         2070.97            -13.2            3.80     -13200.0      3800.0  -9400.0
5         2016-06-15 2016-07-15 2016-07-15               SPX   30      1         10           c    2070         0.49          2070.30         2161.20             39.1          -91.60      39100.0    -91600.0 -52500.0
5         2016-06-15 2016-07-15 2016-07-15               SPX   30     -1         10           c    2105         0.29          2070.30         2161.20            -18.9           61.20     -18900.0     61200.0  42300.0
6         2016-07-20 2016-08-19 2016-08-19               SPX   30      1         10           c    2170         0.51          2174.12         2183.42             24.4          -14.50      24400.0    -14500.0   9900.0
6         2016-07-20 2016-08-19 2016-08-19               SPX   30     -1         10           c    2200         0.29          2174.12         2183.42             -9.3            0.35      -9300.0       350.0  -8950.0
7         2016-08-17 2016-09-16 2016-09-16               SPX   30      1         10           c    2180         0.50          2181.95         2139.01             24.4           -0.05      24400.0       -50.0  24350.0
7         2016-08-17 2016-09-16 2016-09-16               SPX   30     -1         10           c    2210         0.28          2181.95         2139.01             -8.2            0.05      -8200.0        50.0  -8150.0
8         2016-09-21 2016-10-21 2016-10-21               SPX   30      1         10           c    2160         0.51          2163.07         2141.15             30.8           -0.15      30800.0      -150.0  30650.0
8         2016-09-21 2016-10-21 2016-10-21               SPX   30     -1         10           c    2195         0.29          2163.07         2141.15            -10.3            0.05     -10300.0        50.0 -10250.0
9         2016-10-19 2016-11-18 2016-11-18               SPX   30      1         10           c    2145         0.51          2144.29         2181.98             29.5          -41.20      29500.0    -41200.0 -11700.0
9         2016-10-19 2016-11-18 2016-11-18               SPX   30     -1         10           c    2180         0.30          2144.29         2181.98            -10.7           12.50     -10700.0     12500.0   1800.0
10        2016-11-16 2016-12-16 2016-12-16               SPX   30      1         10           c    2175         0.50          2176.95         2258.05             29.0          -84.80      29000.0    -84800.0 -55800.0
10        2016-11-16 2016-12-16 2016-12-16               SPX   30     -1         10           c    2210         0.30          2176.95         2258.05            -11.4           56.30     -11400.0     56300.0  44900.0
...

Total Profit: 39100.0
```

**Full Documentation Coming Soon!**