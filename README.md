[![Test Coverage](https://api.codeclimate.com/v1/badges/37b11e992a6900d30310/test_coverage)](https://codeclimate.com/github/michaelchu/optopsy/test_coverage)
[![Maintainability](https://api.codeclimate.com/v1/badges/37b11e992a6900d30310/maintainability)](https://codeclimate.com/github/michaelchu/optopsy/maintainability)
[![CircleCI](https://circleci.com/gh/michaelchu/optopsy.svg?style=shield)](https://circleci.com/gh/michaelchu/optopsy)
[![Downloads](https://pepy.tech/badge/optopsy)](https://pepy.tech/project/optopsy)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

# Optopsy

Optopsy is a nimble backtesting and statistics library for option strategies, it is designed to answer questions like
"How do straddles perform on the SPX?" or "Which strikes and/or expiration dates should I choose to make the most potential profit?"

Use cases for Optopsy:
* Generate option strategies from raw option chain datasets for your own analysis
* Discover performance statistics on **percentage change** for various options strategies on a given stock
* Run backtests on option strategies based on entry conditions generated from Optopsy (Planned)

## Supported Option Strategies
* Calls/Puts
* Straddles/Strangles
* Vertical Call/Put Spreads
* Butterflies (Planned)
* Iron Condors (Planned)
* Many more to follow

## Documentation
Please see the [wiki](https://github.com/michaelchu/optopsy/wiki) for API reference.

## Usage

### Use Your Data
* Use data from any source, just provide a Pandas dataframe with the required columns when calling optopsy functions.

### Dependencies
You will need Python 3.6 or newer and Pandas 0.23.1 or newer and Numpy 1.14.3 or newer.

### Installation
```
pip install optopsy==2.0.1
```

### Example

Let's see how long calls perform on the SPX on a small demo dataset on the SPX:
Download the following data sample from DeltaNeutral: http://www.deltaneutral.com/files/Sample_SPX_20151001_to_20151030.csv

This dataset is for the month of October in 2015, lets load it into Optopsy. First create a small helper function
that returns a file path to our file. We will store it under a folder named 'data', in the same directory as the working python file.
```
def filepath():
    curr_file = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(curr_file, "./data/Sample_SPX_20151001_to_20151030.csv")
```

Next lets use this function to pass in the file path string into Optopsy's `csv_data()` function, we will map the column
indices using the defined function parameters. We are omitting the `start_date` and `end_date` parameters in this call because
we want to include the entire dataset. The numeric values represent the column number as found in the sample file, the
numbers are 0-indexed:
```
import optopsy as op

spx_data = op.csv_data(
    filepath(),
    underlying_symbol=0,
    underlying_price=1,
    option_type=5,
    expiration=6,
    quote_date=7,
    strike=8,
    bid=10,
    ask=11,
)
```  
The `csv_data()` function is a convenience function. Under the hood it uses Panda's `read_csv()` function to do the import.
There are other parameters that can help with loading the csv data, consult the code/future documentation to see how to use them.

Optopsy is a small simple library that offloads the heavy work of backtesting option strategies, the API is designed to be simple
and easy to implement into your regular Panda's data analysis workflow. As such, we just need to call the `long_calls()` function
to have Optopsy generate all combinations of a simple long call strategy for the specified time period and return a DataFrame. Here we
also use Panda's `round()` function afterwards to return statistics within two decimal places.

```
long_calls_spx_pct_chgs = op.long_calls(spx_data).round(2)
```

The function will returned a Pandas DataFrame containing the statistics on the **percentange changes** of running long calls in all *valid* combinations on the SPX:

|    | dte_range   | otm_pct_range   |   count |   mean |   std |   min |   25% |   50% |   75% |   max |
|----|-------------|-----------------|---------|--------|-------|-------|-------|-------|-------|-------|
|  0 | (0, 7]      | (-0.5, -0.45]   |     155 |   0.03 |  0.02 | -0.02 |  0.01 |  0.02 |  0.04 |  0.11 |
|  1 | (0, 7]      | (-0.45, -0.4]   |     201 |   0.04 |  0.03 | -0.02 |  0.01 |  0.03 |  0.06 |  0.12 |
|  2 | (0, 7]      | (-0.4, -0.35]   |     247 |   0.04 |  0.03 | -0.02 |  0.02 |  0.04 |  0.07 |  0.13 |
|  3 | (0, 7]      | (-0.35, -0.3]   |     296 |   0.05 |  0.04 | -0.02 |  0.02 |  0.04 |  0.08 |  0.15 |
|  4 | (0, 7]      | (-0.3, -0.25]   |     329 |   0.05 |  0.05 | -0.03 |  0.02 |  0.05 |  0.09 |  0.17 |
|  5 | (0, 7]      | (-0.25, -0.2]   |     352 |   0.06 |  0.05 | -0.03 |  0.02 |  0.05 |   0.1 |   0.2 |
|  6 | (0, 7]      | (-0.2, -0.15]   |     383 |   0.08 |  0.07 | -0.04 |  0.03 |  0.07 |  0.13 |  0.26 |
|  7 | (0, 7]      | (-0.15, -0.1]   |     417 |   0.11 |  0.09 | -0.06 |  0.04 |  0.09 |  0.17 |  0.37 |
|  8 | (0, 7]      | (-0.1, -0.05]   |     461 |   0.18 |  0.16 | -0.12 |  0.07 |  0.15 |  0.28 |  0.69 |
|  9 | (0, 7]      | (-0.05, -0.0]   |     505 |   0.64 |  1.03 |    -1 |  0.14 |  0.37 |  0.87 |  7.62 |
| 10 | (0, 7]      | (-0.0, 0.05]    |     269 |   2.34 |  8.65 |    -1 |    -1 | -0.89 |  1.16 |    68 |
| 11 | (0, 7]      | (0.05, 0.1]     |       2 |     -1 |     0 |    -1 |    -1 |    -1 |    -1 |    -1 |
| 12 | (7, 14]     | (-0.5, -0.45]   |      70 |   0.06 |  0.03 |  0.02 |  0.03 |  0.07 |  0.08 |  0.12 |
| 13 | (7, 14]     | (-0.45, -0.4]   |     165 |   0.09 |  0.04 |  0.02 |  0.06 |  0.08 |   0.1 |  0.17 |
| 14 | (7, 14]     | (-0.4, -0.35]   |     197 |   0.09 |  0.04 |  0.02 |  0.07 |  0.09 |  0.12 |  0.19 |
| 15 | (7, 14]     | (-0.35, -0.3]   |     235 |   0.11 |  0.04 |  0.02 |  0.09 |   0.1 |  0.13 |  0.21 |
| 16 | (7, 14]     | (-0.3, -0.25]   |     265 |   0.13 |  0.05 |  0.03 |   0.1 |  0.12 |  0.15 |  0.25 |
| 17 | (7, 14]     | (-0.25, -0.2]   |     280 |   0.15 |  0.06 |  0.03 |  0.11 |  0.14 |  0.18 |   0.3 |
| 18 | (7, 14]     | (-0.2, -0.15]   |     307 |   0.18 |  0.08 |  0.04 |  0.14 |  0.18 |  0.23 |  0.38 |
| 19 | (7, 14]     | (-0.15, -0.1]   |     332 |   0.25 |  0.11 |  0.05 |  0.18 |  0.24 |  0.31 |  0.54 |
| 20 | (7, 14]     | (-0.1, -0.05]   |     370 |    0.4 |  0.18 |  0.07 |  0.29 |  0.39 |  0.52 |  0.97 |
| 21 | (7, 14]     | (-0.05, -0.0]   |     404 |   1.02 |  0.68 | -0.46 |  0.58 |  0.86 |  1.32 |   4.4 |
| 22 | (7, 14]     | (-0.0, 0.05]    |     388 |   1.52 |  4.45 |    -1 | -0.99 | -0.73 |  2.65 |    32 |
| 23 | (7, 14]     | (0.05, 0.1]     |      36 |  -0.93 |  0.06 |    -1 |    -1 | -0.94 | -0.87 | -0.83 |
| 24 | (14, 21]    | (-0.5, -0.45]   |       6 |    0.1 |  0.01 |  0.09 |  0.09 |   0.1 |   0.1 |   0.1 |
| 25 | (14, 21]    | (-0.45, -0.4]   |      66 |   0.14 |  0.04 |  0.09 |  0.11 |  0.14 |  0.17 |  0.23 |
| 26 | (14, 21]    | (-0.4, -0.35]   |      91 |   0.16 |  0.04 |   0.1 |  0.12 |  0.16 |   0.2 |  0.25 |
| 27 | (14, 21]    | (-0.35, -0.3]   |     135 |   0.18 |  0.05 |  0.11 |  0.13 |  0.17 |  0.21 |  0.28 |
| 28 | (14, 21]    | (-0.3, -0.25]   |     149 |    0.2 |  0.05 |  0.12 |  0.15 |   0.2 |  0.25 |  0.33 |
| 29 | (14, 21]    | (-0.25, -0.2]   |     160 |   0.24 |  0.06 |  0.14 |  0.18 |  0.23 |  0.29 |   0.4 |
| 30 | (14, 21]    | (-0.2, -0.15]   |     174 |    0.3 |  0.08 |  0.17 |  0.23 |  0.29 |  0.35 |  0.51 |
| 31 | (14, 21]    | (-0.15, -0.1]   |     187 |    0.4 |  0.11 |  0.22 |   0.3 |  0.38 |  0.48 |   0.7 |
| 32 | (14, 21]    | (-0.1, -0.05]   |     211 |   0.63 |  0.19 |  0.32 |  0.47 |   0.6 |  0.75 |  1.16 |
| 33 | (14, 21]    | (-0.05, -0.0]   |     229 |   1.39 |  0.53 |  0.58 |     1 |   1.3 |  1.73 |   3.1 |
| 34 | (14, 21]    | (-0.0, 0.05]    |     252 |   2.58 |  2.92 |    -1 |    -1 |  2.72 |  4.56 |  10.1 |
| 35 | (14, 21]    | (0.05, 0.1]     |      93 |  -0.82 |  0.92 |    -1 |    -1 |    -1 |    -1 |  6.39 |
| 36 | (21, 28]    | (-0.5, -0.45]   |       1 |   0.11 |   nan |  0.11 |  0.11 |  0.11 |  0.11 |  0.11 |
| 37 | (21, 28]    | (-0.45, -0.4]   |      21 |   0.15 |  0.03 |  0.11 |  0.12 |  0.15 |  0.17 |  0.23 |
| 38 | (21, 28]    | (-0.4, -0.35]   |      39 |    0.2 |  0.06 |  0.12 |  0.16 |  0.18 |  0.24 |  0.32 |
| 39 | (21, 28]    | (-0.35, -0.3]   |      61 |   0.21 |  0.06 |  0.13 |  0.17 |   0.2 |  0.26 |  0.35 |
| 40 | (21, 28]    | (-0.3, -0.25]   |      75 |   0.25 |  0.08 |  0.14 |   0.2 |  0.24 |  0.31 |  0.41 |
| 41 | (21, 28]    | (-0.25, -0.2]   |      79 |    0.3 |  0.09 |  0.17 |  0.23 |  0.27 |  0.37 |  0.49 |
| 42 | (21, 28]    | (-0.2, -0.15]   |      87 |   0.37 |  0.11 |   0.2 |  0.29 |  0.34 |  0.45 |  0.62 |
| 43 | (21, 28]    | (-0.15, -0.1]   |      93 |   0.48 |  0.15 |  0.26 |  0.37 |  0.46 |  0.58 |  0.85 |
| 44 | (21, 28]    | (-0.1, -0.05]   |     105 |   0.74 |  0.24 |  0.36 |  0.56 |  0.71 |  0.89 |  1.39 |
| 45 | (21, 28]    | (-0.05, -0.0]   |     114 |   1.45 |  0.54 |  0.62 |  1.05 |  1.34 |  1.73 |  3.28 |
| 46 | (21, 28]    | (-0.0, 0.05]    |     125 |   2.97 |  3.38 |    -1 |  1.29 |  2.58 |  4.21 | 17.15 |
| 47 | (21, 28]    | (0.05, 0.1]     |      85 |   0.82 |   5.3 |    -1 |    -1 |    -1 |    -1 |  19.5 |
| 48 | (28, 35]    | (-0.4, -0.35]   |       5 |   0.31 |  0.01 |   0.3 |   0.3 |  0.31 |  0.32 |  0.32 |
| 49 | (28, 35]    | (-0.35, -0.3]   |       7 |   0.34 |  0.01 |  0.32 |  0.33 |  0.35 |  0.35 |  0.36 |
| 50 | (28, 35]    | (-0.3, -0.25]   |      12 |   0.39 |  0.02 |  0.36 |  0.37 |  0.39 |   0.4 |  0.42 |
| 51 | (28, 35]    | (-0.25, -0.2]   |      13 |   0.46 |  0.02 |  0.42 |  0.44 |  0.45 |  0.47 |  0.49 |
| 52 | (28, 35]    | (-0.2, -0.15]   |      14 |   0.55 |  0.04 |   0.5 |  0.53 |  0.55 |  0.58 |  0.62 |
| 53 | (28, 35]    | (-0.15, -0.1]   |      15 |   0.73 |  0.07 |  0.63 |  0.67 |  0.72 |  0.77 |  0.84 |
| 54 | (28, 35]    | (-0.1, -0.05]   |      17 |   1.06 |  0.14 |  0.86 |  0.94 |  1.05 |  1.17 |  1.32 |
| 55 | (28, 35]    | (-0.05, -0.0]   |      19 |   1.95 |  0.44 |  1.36 |  1.58 |  1.87 |  2.26 |  2.79 |
| 56 | (28, 35]    | (-0.0, 0.05]    |      20 |   5.72 |  2.23 |  2.94 |  3.85 |  5.23 |  7.33 |  9.97 |
| 57 | (28, 35]    | (0.05, 0.1]     |      21 |   3.53 |  5.47 |    -1 |    -1 |    -1 | 10.38 | 11.32 |

There are more customization options for Optopsy's strategy functions, consult the codebase/future documentation to see how it can be used to adjust the results, such as increasing/decreasing
the intervals and other data to be returned.

The library is currently under development, as such expect changes to the API in the future.

