import optopsy as op


def run_strategy():
    # fetch the option chains from our data source
    data = op.get(
        'data/SPX.csv',
        struct=op.Struct.CBOE,
        prompt=False
    )
    
    entry_filters = {'dte': op.Period.SEVEN_WEEKS, 'price': 1.0}
    exit_filters = {}

    # test our strategy with our defined filter rules,
    # simulate function will return a dict with three dataframe items: summary, returns
    # and trades
    backtest = op.simulate('Weekly Verticals', 
						   "long_call_spread",
						   entry_filters=entry_filters,
						   exit_filters=exit_filters
					      )


if __name__ == '__main__':
    run_strategy()
