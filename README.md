# Development Update (June 1, 2018)

This library is currently being redeveloped to be better optimized for options backtesting. 

The new version will provide predefined filters to act as building blocks for your option trading strategies.
No need to extend classes to implement custom trade configurations such as position sizing and commissions. These
settings can now be defined using existing filters.

Filters will include (but not limited to):

**Entry rules:**
* Days to expiration,
* Entry Days (Stagger trades)
* Absolute Delta
* Percentage out-of-the-money.
* Contract size

**Exit rules:**
* Days to expiration
* Hold days
* Profit/Stop loss percent
* Spread delta
* Spread price

Development changes will be made on the `development` branch

# Optopsy

This library allows you to backtest options strategies with your own historical options data. 
Use the built-in filters to generate options spreads with adjustable parameters and backtest them with your own custom entry / exit criterion.

## Features
* **Open source** - Feel free to make requests or contribute to the code base! Help out a fellow trader!
* **BYOD** - "Bring your own Data" source by using the built-in data adapters or write your own. (Currently supports csv files)
* **Optimization support** - Define ranges for your strategy parameters and the system will execute the strategy for each value of the range

### Planned Features
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

### Usage

Coming Soon.