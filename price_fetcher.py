"""
price_fetcher.py — yfinance Live Price Layer with Offline Cache
Stock Portfolio Analyzer
"""

import datetime
import pandas as pd
import database as db

try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def _yf_symbol(symbol: str) -> str:
    """
    Convert plain symbol to Yahoo Finance ticker.
    Example:
        RELIANCE -> RELIANCE.NS
        TCS -> TCS.NS
        RELIANCE.NS -> RELIANCE.NS
    """

    s = symbol.upper().strip()

    # ✅ FIX: Validate non-empty string
    if not s:
        return None

    if "." not in s:
        return s + ".NS"

    return s


def fetch_prices(symbols: list) -> dict:
    """
    Fetch live prices using Yahoo Finance Ticker API.
    Avoids MultiIndex issues from yf.download().

    Returns:
    {
        symbol: {
            ltp,
            high,
            low,
            prev_close,
            volume
        }
    }
    """

    # ✅ FIX: Initialize cache with empty dict as fallback
    cache = db.get_price_cache() or {}
    result = {}

    if not YFINANCE_AVAILABLE:
        print("yfinance not installed")
        return result

    if not symbols:
        return result

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for sym in symbols:

        try:

            ticker_symbol = _yf_symbol(sym)

            # ✅ FIX: Check if symbol conversion was successful
            if not ticker_symbol:
                print(f"Invalid symbol: {sym}")
                result[sym] = cache.get(sym, {
                    "ltp": 0,
                    "high": 0,
                    "low": 0,
                    "prev_close": 0,
                    "volume": 0
                })
                continue

            print("\n===================================")
            print("Original Symbol:", sym)
            print("Yahoo Ticker:", ticker_symbol)

            ticker = yf.Ticker(ticker_symbol)

            df = ticker.history(
                period="5d",
                auto_adjust=False
            )

            print(df.tail())

            if df is None or df.empty:
                raise ValueError("No data returned from Yahoo Finance")

            latest = df.iloc[-1]

            ltp = float(latest["Close"])
            high = float(latest["High"])
            low = float(latest["Low"])

            if len(df) >= 2:
                prev_close = float(df.iloc[-2]["Close"])
            else:
                prev_close = ltp

            # ✅ FIX: Use proper pandas Series access, not .get()
            try:
                volume = float(latest["Volume"])
            except (KeyError, TypeError, ValueError):
                volume = 0

            print(f"LTP = {ltp}")

            db.update_price_cache(
                sym,
                ltp,
                high,
                low,
                prev_close,
                volume,
                now
            )

            result[sym] = {
                "ltp": ltp,
                "high": high,
                "low": low,
                "prev_close": prev_close,
                "volume": volume
            }

        except Exception as e:

            print(f"Price fetch error for {sym}: {e}")

            # ✅ FIX: Safe cache access with proper fallback
            if sym in cache and isinstance(cache[sym], dict):
                result[sym] = cache[sym]
            else:
                result[sym] = {
                    "ltp": 0,
                    "high": 0,
                    "low": 0,
                    "prev_close": 0,
                    "volume": 0
                }

    print("\nFinal Result:")
    print(result)

    return result


def fetch_history(symbol: str, period: str = "2y"):
    """
    Fetch historical OHLCV data for charts and prediction.

    Returns:
        DataFrame with DatetimeIndex or None on error
    """

    if not YFINANCE_AVAILABLE:
        print("yfinance not installed")
        return None

    try:

        ticker_symbol = _yf_symbol(symbol)

        # ✅ FIX: Validate symbol conversion
        if not ticker_symbol:
            print(f"Invalid symbol: {symbol}")
            return None

        print("Downloading history:", ticker_symbol)

        ticker = yf.Ticker(ticker_symbol)

        df = ticker.history(
            period=period,
            auto_adjust=False
        )

        if df is None or df.empty:
            print("No historical data found")
            return None

        print("Rows downloaded:", len(df))

        required_cols = [
            "Open",
            "High",
            "Low",
            "Close"
        ]

        for col in required_cols:

            if col not in df.columns:
                print("Missing column:", col)
                return None

        # ✅ FIX: Ensure DatetimeIndex for consistency
        if not isinstance(df.index, pd.DatetimeIndex):
            print("Warning: Index is not DatetimeIndex, converting...")
            df.index = pd.to_datetime(df.index)

        return df

    except Exception as e:

        print("fetch_history error:", e)
        return None
