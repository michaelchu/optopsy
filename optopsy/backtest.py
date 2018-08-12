import optopsy.option_strategy as os


# this is the main function that runs the backtest engine
def simulate(title, data, u_filters):
    # call the appropriate option strategy function based on the 'strategy'
    # attribute of the filter
    strategy = u_filters['strategy']
    if strategy is not None:
        orders = getattr(os, strategy)(data, u_filters)
    else:
        raise ValueError("Strategy not provided!")

    # option strategy function will create option spreads that match the entry
    # filter's parameters

    # filter the main option chain for only the options that are used to create the spreads

    # search the main option chain for options that match the exit criteria

    # if exit criterion are met for all legs of the spread, simulate a sell action
