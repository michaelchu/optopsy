from .basecsvfeed import BaseCSVFeed


class CboeCSVFeed(BaseCSVFeed):

        params = (
            ('symbol', 0),
            ('underlying_symbol', 1),
            ('quote_date', 2),
            ('root', 1),
            ('expiration', 4),
            ('strike', 5),
            ('option_type', 6),
            ('open', -1),
            ('high', -1),
            ('low', -1),
            ('close', -1),
            ('trade_volume', 11),
            ('bid_size', -1),
            ('bid', 13),
            ('ask_size', -1),
            ('ask', 15),
            ('underlying_price', 16),
            ('implied_vol', -1),
            ('delta', 18),
            ('gamma', 19),
            ('theta', 20),
            ('vega', 21),
            ('rho', 22),
            ('open_interest', -1)
        )
