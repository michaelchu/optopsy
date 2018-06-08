# -*- coding: utf-8 -*-
import pyprind


class Optopsy(object):

    def __init__(self, strategy, data, name=None,
                 init_capital=10000, progress_bar=True):
        self.strategy = strategy
        self.data = data
        self.dates = data.index.unique()
        self.capital = init_capital
        self.name = name if not None else self.strategy.name

    def run(self, progress_bar=True):
        """
        Here we will generate a list of strategies to execute based on any optimization
        parameters given in filters.
        :return:
        """

        # First we set the strategy's available capital
        self.strategy.adjust(self.capital)
        
        # Pass the data to the strategy, to setup the option spread
        self.strategy.setup(self.data)
        
        # init progress bar
        if progress_bar:
            bar = pyprind.ProgBar(len(self.dates), title=self.name, stream=1, bar_char='█')

        for dt in self.dates:

            # update progress bar
            if progress_bar:
                bar.update()

            if not self.strategy.bankrupt:
                self.strategy.update(dt)
            else:
                if progress_bar:
                    bar.stop()

        print('\nDone!')
