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
    

class FilterStack(Filter):

    """
    An FilterStack derives from Filter runs multiple Filters until a
    failure is encountered.

    The purpose of an FilterStack is to group a logic set of Filters together. Each
    Filter in the stack is run. Execution stops if one Filter returns False.

    Args:
        * filters (list): List of filters.

    """

    def __init__(self, *filters):
        super(FilterStack, self).__init__()
        self.filters = filters
        self.check_run_always = any(hasattr(x, 'run_always')
                                    for x in self.filters)

    def __call__(self, target):
        # normal running mode
        if not self.check_run_always:
            for filter in self.filters:
                if not filter(target):
                    return False
            return True
        # run mode when at least one filter has a run_always attribute
        else:
            # store result in res
            # allows continuation to check for and run
            # filters that have run_always set to True
            res = True
            for filter in self.filters:
                if res:
                    res = filter(target)
                elif hasattr(filter, 'run_always'):
                    if filter.run_always:
                        filter(target)
            return res


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
