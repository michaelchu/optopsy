class Broker(object):

    def __init__(self):
        self.balance = 10000

    def set_cash(self, amount):
        self.balance = amount

    def get_value(self):
        return self.balance
