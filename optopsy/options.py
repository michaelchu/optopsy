class Options(object):

    def __init__(self, data):
        pass


class LongCall(Options):

    def __init__(self, data):
        super(LongCall, self).__init__(data)


class ShortCall(Options):

    def __init__(self, data):
        super(ShortCall, self).__init__(data)


class LongPut(Options):

    def __init__(self, data):
        super(LongPut, self).__init__(data)


class ShortPut(Options):

    def __init__(self, data):
        super(ShortPut, self).__init__(data)


class LongCallSpread(Options):

    def __init__(self, data, width):
        super(LongCallSpread, self).__init__(data)
        self.width = width


class ShortCallSpread(Options):

    def __init__(self, data, width):
        super(ShortCallSpread, self).__init__(data)
        self.width = width


class LongPutSpread(Options):

    def __init__(self, data, width):
        super(LongPutSpread, self).__init__(data)
        self.width = width


class ShortPutSpread(Options):

    def __init__(self, data, width):
        super(ShortPutSpread, self).__init__(data)
        self.width = width


class LongIronCondor(Options):

    def __init__(self, data, width, width_c, width_p):
        super(LongIronCondor, self).__init__(data)
        self.width = width
        self.width_c = width_c
        self.width_p = width_p


class ShortIronCondor(Options):

    def __init__(self, data, width, width_c, width_p):
        super(ShortIronCondor, self).__init__(data)
        self.width = width
        self.width_c = width_c
        self.width_p = width_p
