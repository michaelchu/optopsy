import datetime
import os.path
import sys
# import the backtest library
import optopsy as op


class SampleStrategy(op.Strategy):

    def on_init(self, **params):

        self.set_strategy_name("Sample Strategy")

        # add vertical put spreads for this strategy
        self.add_option_strategy(
            "VXX",
            op.OptionStrategy.VERTICAL,
            option_type=op.OptionType.PUT,
            width=self.width,
            dte=self.dte
        )

    def on_data(self, data):
        pass

    def on_fill(self, event):
        pass

    def filter_options(self, data):
        strategy = data['VXX'].nearest('mark', 1).max('dte')
        self.buy_to_open(strategy, 10, order_type=op.OrderType.LMT, price=0.75)


if __name__ == '__main__':

    # Create an instance of Optopsy
    optopsy = op.Backtest()

    # Add a strategy/optimize strategy
    optopsy.addStrategy(SampleStrategy)

    # Add optimization
    # optopsy.addOptStrategy(SampleStrategy, width=(2, 3, 4))

    # Data are in a sub-folder of the strategies folder. Find where this script is run,
    # and look for the sub-folder. This script can reside anywhere.
    currpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(currpath, 'data/vix.csv')

    # Create a Data Feed
    data = op.feeds.CboeCSVFeed(
        dataname=datapath,
        # Do not pass values before this date
        fromdate=datetime.datetime(2000, 1, 1),
        # Do not pass values after this date
        todate=datetime.datetime(2000, 12, 31)
    )

    # Add the Data Feed to Optopsy
    optopsy.addData(data)

    # Set our desired cash start
    optopsy.broker.setcash(100000.0)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % optopsy.broker.getvalue())

    # Run over everything
    optopsy.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % optopsy.broker.getvalue())
