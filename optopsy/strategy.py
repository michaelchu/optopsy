class Strategy(object):

    def __init__(self, filters):

        # Here we filter out params labeled 'entry' to be assigned to internal
        # entry filters
        self.strategy = [f for f in filters if 'strategy' in f]
        self.entry_filters = [f for f in filters if 'entry' in f]
        self.exit_filters = [f for f in filters if 'entry' in f]



