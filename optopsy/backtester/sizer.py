class DefaultSizer(object):

    def __init__(self, broker, account):
        self.broker = broker
        self.account = account

    def fixed(self, amount=1):
        return amount

