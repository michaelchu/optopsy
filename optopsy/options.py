from .option_query import *


class Option(object):

    def __init__(self, name=None):
        self.name = name


class Single(Option):

    def __init__(self, option_type):
        super(Single, self).__init__('Single')
        self.option_type = option_type

    def __call__(self, data, target):
        # here we generate the spread and assign the results to the target
        query = OptionQuery(data).calls()
        print(query.option_chain.head())


class ShortCall(Option):

    def __init__(self, data):
        super(ShortCall, self).__init__(data)


class LongPut(Option):

    def __init__(self, data):
        super(LongPut, self).__init__(data)


class ShortPut(Option):

    def __init__(self, data):
        super(ShortPut, self).__init__(data)


class LongCallSpread(Option):

    def __init__(self, data, width):
        super(LongCallSpread, self).__init__(data)
        self.width = width


class ShortCallSpread(Option):

    def __init__(self, data, width):
        super(ShortCallSpread, self).__init__(data)
        self.width = width


class LongPutSpread(Option):

    def __init__(self, data, width):
        super(LongPutSpread, self).__init__(data)
        self.width = width


class ShortPutSpread(Option):

    def __init__(self, data, width):
        super(ShortPutSpread, self).__init__(data)
        self.width = width


class LongIronCondor(Option):

    def __init__(self, data, width, width_c, width_p):
        super(LongIronCondor, self).__init__(data)
        self.width = width
        self.width_c = width_c
        self.width_p = width_p


class ShortIronCondor(Option):

    def __init__(self, data, width, width_c, width_p):
        super(ShortIronCondor, self).__init__(data)
        self.width = width
        self.width_c = width_c
        self.width_p = width_p
