class Algo(object):

    """
    Algos are used to modularize strategy logic so that strategy logic becomes
    modular, composable, more testable and less error prone. Basically, the
    Algo should follow the unix philosophy - do one thing well.
    In practice, algos are simply a function that receives one argument, the
    Strategy (referred to as target) and are expected to return a bool.
    When some state preservation is necessary between calls, the Algo
    object can be used (this object). The __call___ method should be
    implemented and logic defined therein to mimic a function call. A
    simple function may also be used if no state preservation is necessary.
    Args:
        * name (str): Algo name
    """

    def __init__(self, name=None):
        self._name = name

    @property
    def name(self):
        """
        Algo name.
        """
        if self._name is None:
            self._name = self.__class__.__name__
        return self._name

    def __call__(self, target):
        raise NotImplementedError("%s not implemented!" % self.name)


class DataFeed(Algo):

    """
    Sets the date range for data passed to the strategy
    """

    def __init__(self, file_path, data_struct):
        super(DataFeed, self).__init__()
        self.file_path = file_path
        self.data_struct = data_struct

    def __call__(self, target):
        return True


class DateRange(Algo):

    """
    Sets the date range for data passed to the strategy
    """

    def __init__(self, start_date, end_date):
        super(DateRange, self).__init__()
        self.start_date = start_date
        self.end_date = end_date

    def __call__(self, target):
        if self.start_date < self.end_date:
            return False
        return True
