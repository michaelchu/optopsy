from optopsy.enums import FilterType


class Filter(object):

    def __init__(self, name=None):
        self._name = name
        self.type = None

    @property
    def name(self):
        """
        Filter name.
        """
        if self._name is None:
            self._name = self.__class__.__name__
        return self._name

    def __call__(self, target, quotes):
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

    def __init__(self, target, *filters):
        super(FilterStack, self).__init__()
        self.filters = filters
        self.check_run_always = any(hasattr(x, 'run_always')
                                    for x in self.filters)

        # check if our data source has columns needed for certain filters
        for f in self.filters:
            if hasattr(f, 'required_fields'):
                if not all(fld in target.spread_data.columns for fld in f.required_fields):
                    raise ValueError("Required fields: %, not in data source" % f.required_fields)

    def __call__(self, target, quotes):
        # normal running mode
        if not self.check_run_always:
            for f in self.filters:
                if not f(target, quotes):
                    return False
            return True
        # run mode when at least one filter has a run_always attribute
        else:
            # store result in res
            # allows continuation to check for and run
            # filters that have run_always set to True
            res = True
            for f in self.filters:
                if res:
                    res = f(target, quotes)
                elif hasattr(f, 'run_always'):
                    if f.run_always:
                        f(target)
            return res


class EntryAbsDelta(Filter):

    def __init__(self, ideal, lower, upper):
        super(EntryAbsDelta).__init__()
        self.__setattr__('type', FilterType.ENTRY)
        self.__setattr__('required_fields', ['delta'])
        self.ideal = ideal
        self.lower = lower
        self.upper = upper

    def __call__(self, target, quotes):
        pass


class EntrySpreadPrice(Filter):

    def __init__(self, ideal, lower, upper):
        super(EntrySpreadPrice).__init__()
        self.__setattr__('type', FilterType.ENTRY)
        self.ideal = ideal
        self.lower = lower
        self.upper = upper

    def __call__(self, target, quotes):

        pass


class EntryDaysToExpiration(Filter):

    def __init__(self, ideal, lower, upper):
        super(EntryDaysToExpiration).__init__()
        self.__setattr__('type', FilterType.ENTRY)
        self.ideal = ideal
        self.lower = lower
        self.upper = upper

    def __call__(self, target, quotes):
        pass


class EntryDayOfWeek(Filter):

    def __init__(self, ideal):
        super(EntryDayOfWeek).__init__()
        self.__setattr__('type', FilterType.ENTRY)
        self.ideal = ideal

    def __call__(self, target, quotes):
        pass


class ExitDaysToExpiration(Filter):

    def __init__(self, ideal):
        super(ExitDaysToExpiration).__init__()
        self.__setattr__('type', FilterType.EXIT)
        self.ideal = ideal

    def __call__(self, target, quotes):
        pass

