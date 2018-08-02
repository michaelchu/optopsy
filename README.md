# Development Update (June 1, 2018)

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/2de8f5b3fa2742de93fb60b3a1ae5683)](https://app.codacy.com/app/michaelchu/optopsy?utm_source=github.com&utm_medium=referral&utm_content=michaelchu/optopsy&utm_campaign=badger)
[![Build Status](https://travis-ci.org/michaelchu/optopsy.svg?branch=master)](https://travis-ci.org/michaelchu/optopsy)
[![codecov](https://codecov.io/gh/michaelchu/optopsy/branch/master/graph/badge.svg)](https://codecov.io/gh/michaelchu/optopsy)

This library is currently being redeveloped to be better optimized for options backtesting. 

The new version will provide predefined filters to act as building blocks for your option trading strategies.
No need to extend classes to implement custom trade configurations such as position sizing and commissions. These
settings can now be defined using existing filters.

Filters will include (but not limited to):

**Entry rules:**
* Days to expiration
* Entry Days (Stagger trades)
* Absolute Delta
* Percentage out-of-the-money
* Contract size

**Exit rules:**
* Days to expiration
* Hold days
* Profit/Stop loss percent
* Spread delta
* Spread price

Development changes will be made on the `development` branch. The backtester branch will be retained for historical
purposes and will be removed at a later time.

# Optopsy

Optopsy is a flexible backtesting framework used to test complex options trading strategies written in Python. 
Backtesting is the process of testing a strategy over a given data set. This framework allows you to mix and match 
different 'filters' to create a 'Strategy', and allow multiple strategies to form an overall more complex trading algorithms. 
The modular nature of this framework aims to foster the creation of easily testable, re-usable and flexible blocks of strategy logic to facilitate 
the rapid development of complex options trading strategies.

## Features
* **Open source** - Feel free to make requests or contribute to the code base! Help out a fellow trader!
* **BYOD** - "Bring your own Data" source by using the built-in data adapters or write your own. (Currently supports csv files)
* **Modular Design** - Facilitates the construction and composition of complex algorithmic trading strategies that are modular and re-usable.
* **Optimization support** - Define ranges for your strategy parameters and the system will optimize the strategy

### Planned Features
* Indicator Support - Create entry and exit rules based on indicators
* Optimizer - Allows users to run multiple backtests with different combinations of parameters
* Option strategy support:
    * Single Calls/Puts
    * Vertical Spreads
    * Iron Condors (Iron Butterflies)
    * Covered Stock
    * Combos (Synthetics/Collars)
    * Diagonal Spreads
    * Calendar Spreads
    * Custom Spreads
    * Strangles
    * Straddles
 * Stock Price Distribution Generator - Analyze historical stock price movements patterns to discover potential trade ideas.
 * Trade Scanner - Used to recommend trades based on stock price distributions

### Dependencies
You will need Python 3.6.x. It is recommended to install [Miniconda3](https://conda.io/miniconda.html). See [requirements.txt](https://github.com/michaelchu/optopsy/blob/master/requirements.txt) for full details.

### Installation
```
pip install optopsy
```

### Usage
```
python strategies/sample_strategy.py
```
The sample strategy can be used with [Level 3 Historical CSV Data Sample](https://www.historicaloptiondata.com/content/sample-files-0?gclid=CjwKCAjwtIXbBRBhEiwAWV-5ngKHMIxUw_rCK1DnkQpS4BUs_XQmLG09hm4SWpE9FoMJc3hb6qMPqhoCGgIQAvD_BwE) from historicaloptiondata.com. 

In order to use it, you will need to define the struct variable to map the column names to the numerical index as per the file format.

