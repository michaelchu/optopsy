# Optopsy

This library allows you to backtest options strategies with your own historical options data. Use the built-in functions to generate options spreads with adjustable parameters and backtest them with your own custom entry / exit / adjustment criteria.

## Features
* Uses Pandas library under the hood to generate options spreads efficiently.
* Option spreads can be generated with adjustable parameters such as strike width and expiration dates. This allows you to create more advance strategies such as broken-wing butterflies/iron condors
* Generates historical option spread prices for all possible strike combinations from the option chain.
* Use your own options data source by using the built-in data adapters or write your own. (Currently supports sqlite)
* Integrated brokerage simulation with market and limit orders
* Interchangeable and extensible position sizers, slippage and commissions modules (WIP)
* Optimization support: define a range for your strategy parameters and the system will execute the strategy for each value of the range
* The following options strategies are currently supported:
    * Single Calls/Puts
    * Vertical Spreads

### Planned Features
* CSV file support
* Option strategy support:
    * Iron Condors (Iron Butterflies)
    * Covered Stock
    * Combos (Synthetics/Collars)
    * Diagonal Spreads
    * Calendar Spreads
    * Custom Spreads
    * Strangles
    * Straddles

## Installation

### Quick start

To set up a development environment quickly, first install Python 3. It
comes with virtualenv built-in. So create a virtual env by:

    1. `$ python3 -m venv optopsy`
    2. `$ . optopsy/bin/activate`

Install all dependencies:

    pip install -r requirements.txt

### Notes

It is recommended to use the Anaconda distribution to install the projects dependencies.

### Usage

Coming Soon.