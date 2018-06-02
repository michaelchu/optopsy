from .abstract_data_feed import AbstractDataFeed
from ..option_strategy import *

import pandas as pd


class BaseCSVFeed(AbstractDataFeed):
    """
    Parses a CSV file according to the order and field presence defined by the parameters
    This class will take care of opening the file and reading the file into a dataframe
    """

    def __init__(self, file_path=None, headers=True):
        self.file_path = file_path
        self.headers = headers
        super().__init__()

    def _start(self):
        df = pd.read_csv(self.file_path, self.headers)

    def _get_strategy(self, strategy):
        pass

    def next(self):
        pass
