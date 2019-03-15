[![Downloads](https://pepy.tech/badge/optopsy)](https://pepy.tech/project/optopsy)
[![Build Status](https://travis-ci.org/michaelchu/optopsy.svg?branch=master)](https://travis-ci.org/michaelchu/optopsy)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

# Optopsy

Optopsy is a nimble backtesting libary for option strategies, it is designed to act as an API for your option chain datasets and allows you to focus on what matters, your trading strategy.

The library is designed to compose well into your data analysis work and uses Pandas extensively under the hood. It extends PandasObject to faciliate common functional composition used in quant finance. **As such, please note that importing `optopsy` modifies `pandas.core.base.PandasObject` to provide added functionality to pandas objects, including DataFrames.**

*This library is currently in development, please use at your own risk*

## Usage

### Use Your Data
* Use data from any source, just provide a Pandas dataframe with the required columns when calling optopsy functions.

### Advanced Backtest Parameters:

* Optopsy allows you to mix and match different 'filters' to create an option strategy. Results will be returned as Pandas dataframes so that complex strategies can be composed upon. It is highly encourage to make use of `pandas.DataFrame.pipe` functions and chain methods wherever possible make your code cleaner. To learn more about the subject, I highly recommend reading the following blog [post](https://tomaugspurger.github.io/method-chaining.html).

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
You will need Python 3.7.x and Pandas 0.24.1 or newer. It is recommended to install [Miniconda3](https://conda.io/miniconda.html). See [requirements.txt](https://github.com/michaelchu/optopsy/blob/master/requirements.txt) for full details.

### Installation
```
pip install optopsy
```

### Usage
Optopsy is best used with Jupyter notebooks, however, it is also possible to incorporate it into your python scripts:

The following example uses [Level 2 Historical CSV Data Sample](http://www.deltaneutral.com/files/Sample_SPX_20151001_to_20151030.csv) from historicaloptiondata.com.

**Full Documentation Coming Soon!**
