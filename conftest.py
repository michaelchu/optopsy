"""Root conftest: mock pandas_ta when it's not installable (Python < 3.12)."""

import sys
import types

try:
    import pandas_ta  # noqa: F401
except (ImportError, ModuleNotFoundError, Exception):
    import numpy as np
    import pandas as pd

    pta = types.ModuleType("pandas_ta")
    pta.version = "0.0.0-mock"

    def _rsi(prices, length=14):
        delta = prices.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / length, min_periods=length).mean()
        avg_loss = loss.ewm(alpha=1 / length, min_periods=length).mean()
        rs = avg_gain / avg_loss
        result = 100 - (100 / (1 + rs))
        result.iloc[:length] = float("nan")
        return result

    def _sma(prices, length=20):
        return prices.rolling(length).mean()

    def _ema(prices, length=20):
        if len(prices) < length:
            return None
        return prices.ewm(span=length, adjust=False).mean()

    def _macd(prices, fast=12, slow=26, signal=9):
        if len(prices) < slow + signal:
            return None
        fast_ema = prices.ewm(span=fast, adjust=False).mean()
        slow_ema = prices.ewm(span=slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return pd.DataFrame(
            {
                f"MACD_{fast}_{slow}_{signal}": macd_line,
                f"MACDs_{fast}_{slow}_{signal}": signal_line,
                f"MACDh_{fast}_{slow}_{signal}": histogram,
            },
            index=prices.index,
        )

    def _bbands(prices, length=20, std=2.0):
        mid = prices.rolling(length).mean()
        std_dev = prices.rolling(length).std()
        upper = mid + std * std_dev
        lower = mid - std * std_dev
        return pd.DataFrame(
            {
                f"BBU_{length}_{std}_{std}": upper,
                f"BBM_{length}_{std}_{std}": mid,
                f"BBL_{length}_{std}_{std}": lower,
            },
            index=prices.index,
        )

    def _atr(high, low, close, length=14):
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(length).mean()

    pta.rsi = _rsi
    pta.sma = _sma
    pta.ema = _ema
    pta.macd = _macd
    pta.bbands = _bbands
    pta.atr = _atr

    sys.modules["pandas_ta"] = pta
