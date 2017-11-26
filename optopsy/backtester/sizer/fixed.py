from optopsy.backtester.sizer.base import AbstractPositionSizer


class FixedPositionSizer(AbstractPositionSizer):
    def __init__(self, default_quantity=10):
        self.default_quantity = default_quantity

    def size_order(self, order, account):
        """
        This FixedPositionSizer object simply modifies
        the quantity to be 100 of any share transacted.
        """
        order.quantity = self.default_quantity
        return order
