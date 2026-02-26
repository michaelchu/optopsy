"""Tests for IV rank signal edge cases."""

import pandas as pd

from optopsy.signals import iv_rank_above


class TestIVRankEdgeCases:
    def test_iv_rank_empty_after_dte_filter(self):
        """When all options have DTE <= 0, iv_rank signal returns all-False.

        This hits _compute_atm_iv line 552 (empty after DTE > 0 filter)
        and _iv_rank_signal line 621 (empty ATM IV → return all-False).
        """
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        # All expirations are on or before the quote_date (DTE <= 0)
        data = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"] * 3,
                "quote_date": dates,
                "underlying_price": [100.0, 100.0, 100.0],
                "strike": [100.0, 100.0, 100.0],
                "option_type": ["call", "call", "call"],
                "expiration": dates,  # same as quote_date → DTE = 0
                "implied_volatility": [0.20, 0.25, 0.22],
            }
        )
        sig = iv_rank_above(threshold=0.5)
        result = sig(data)
        assert not result.any()
