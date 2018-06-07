class Filter(object):

    def __init__(self, name=None):
        self._name = name

    @property
    def name(self):
        """
        Filter name.
        """
        if self._name is None:
            self._name = self.__class__.__name__
        return self._name

    def __call__(self, target):
        raise NotImplementedError("%s not implemented!" % self.name)


class EntryAbsDelta(Filter):

    def __init__(self, ideal, min, max):
        super(EntryAbsDelta).__init__()
        self.ideal = ideal
        self.min = min
        self.max = max

    def __call__(self, target):
        pass


class EntrySpreadPrice(Filter):

    def __init__(self, ideal, min, max):
        super(EntrySpreadPrice).__init__()
        self.ideal = ideal
        self.min = min
        self.max = max

    def __call__(self, target):
        pass


class EntryDaysToExpiration(Filter):

    def __init__(self, ideal, min, max):
        super(EntryDaysToExpiration).__init__()
        self.ideal = ideal
        self.min = min
        self.max = max

    def __call__(self, target):
        pass


class EntryDayOfWeek(Filter):

    def __init__(self, ideal):
        super(EntryDayOfWeek).__init__()
        self.ideal = ideal
        self.min = min
        self.max = max

    def __call__(self, target):
        pass
