
"""
price_fetcher.py — yfinance Live Price Layer with Offline Cache
Stock Portfolio Analyzer
"""

import datetime
import pandas as pd
import database as db
import concurrent.futures

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

    # Handle US indices / Cryptos / Foreign stocks that already have dots or hyphens
    if "." not in s and "-" not in s:
        # Default suffix for Indian markets (NSE)
        return s + ".NS"

    return s


def _fetch_single_price(sym: str, cache: dict, now: str) -> tuple:
    """
    Worker function to fetch single ticker data in a thread.
    Returns (symbol, data_dict) with a 'success' flag.
    """
    try:
        ticker_symbol = _yf_symbol(sym)

        # ✅ FIX: Check if symbol conversion was successful
        if not ticker_symbol:
            print(f"Invalid symbol: {sym}")
            return sym, {
                "ltp": 0, "high": 0, "low": 0, "prev_close": 0, "volume": 0,
                "success": False
            }

        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="5d", auto_adjust=False)

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

        try:
            volume = float(latest["Volume"])
        except (KeyError, TypeError, ValueError):
            volume = 0

        return sym, {
            "ltp": ltp,
            "high": high,
            "low": low,
            "prev_close": prev_close,
            "volume": volume,
            "success": True
        }

    except Exception as e:
        print(f"Price fetch error for {sym}: {e}")
        # ✅ FIX: Safe cache access with proper fallback
        if sym in cache and isinstance(cache[sym], dict):
            fallback = cache[sym].copy()
        else:
            fallback = {
                "ltp": 0, "high": 0, "low": 0, "prev_close": 0, "volume": 0
            }
        fallback["success"] = False
        return sym, fallback


def fetch_prices(symbols: list) -> dict:
    """
    Fetch live prices concurrently using Yahoo Finance Ticker API.
    Updates the database price cache in a thread-safe sequential manner.
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

    # Limit maximum workers to prevent rate-limiting and thread overhead
    max_workers = min(10, len(symbols))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_sym = {executor.submit(_fetch_single_price, sym, cache, now): sym for sym in symbols}
        
        for future in concurrent.futures.as_completed(future_to_sym):
            sym = future_to_sym[future]
            try:
                sym_res, data = future.result()
                success = data.pop("success", False)
                result[sym_res] = data

                # Database updates must run sequentially on this thread to avoid locked SQLite connections
                if success:
                    db.update_price_cache(
                        sym_res,
                        data["ltp"],
                        data["high"],
                        data["low"],
                        data["prev_close"],
                        data["volume"],
                        now
                    )
            except Exception as e:
                print(f"Concurrent execution failed for {sym}: {e}")
                # Fallback to cache
                if sym in cache and isinstance(cache[sym], dict):
                    result[sym] = cache[sym]
                else:
                    result[sym] = {
                        "ltp": 0, "high": 0, "low": 0, "prev_close": 0, "volume": 0
                    }

    return result


def fetch_history(symbol: str, period: str = "2y") -> pd.DataFrame:
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
        df = ticker.history(period=period, auto_adjust=False)

        if df is None or df.empty:
            print("No historical data found")
            return None

        print("Rows downloaded:", len(df))

        required_cols = ["Open", "High", "Low", "Close"]
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


def fetch_info(symbol: str) -> dict:
    """
    Fetch company fundamental metadata from Yahoo Finance.
    Returns a unified fundamentals dictionary.
    """
    result = {
        "symbol": symbol.upper().strip(),
        "company": "",
        "sector": "Unknown",
        "industry": "Unknown",
        "market_cap": 0.0,
        "pe_ratio": 0.0,
        "beta": 0.0,
        "fifty_two_week_high": 0.0,
        "fifty_two_week_low": 0.0,
        "dividend_yield": 0.0,
        "error": None
    }

    if not YFINANCE_AVAILABLE:
        result["error"] = "yfinance not installed"
        return result

    try:
        ticker_symbol = _yf_symbol(symbol)
        if not ticker_symbol:
            result["error"] = "Invalid symbol"
            return result

        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        # Handle empty/unreachable info blocks gracefully
        if not info or not isinstance(info, dict):
            # Try history as alternative check
            df = ticker.history(period="1d")
            if df is not None and not df.empty:
                result["company"] = ticker_symbol
                return result
            else:
                result["error"] = "No info or history returned"
                return result

        result["company"] = info.get("longName") or info.get("shortName") or ticker_symbol
        result["sector"] = info.get("sector") or "Unknown"
        result["industry"] = info.get("industry") or "Unknown"
        result["market_cap"] = float(info.get("marketCap") or 0)
        result["pe_ratio"] = float(info.get("trailingPE") or info.get("forwardPE") or 0)
        result["beta"] = float(info.get("beta") or 0)
        result["fifty_two_week_high"] = float(info.get("fiftyTwoWeekHigh") or 0)
        result["fifty_two_week_low"] = float(info.get("fiftyTwoWeekLow") or 0)
        result["dividend_yield"] = float(info.get("dividendYield") or 0)

    except Exception as e:
        result["error"] = str(e)

    return result


def validate_symbol(symbol: str) -> bool:
    """
    Validate if a ticker symbol is recognized and active on Yahoo Finance.
    """
    if not YFINANCE_AVAILABLE:
        return False
    try:
        ticker_symbol = _yf_symbol(symbol)
        if not ticker_symbol:
            return False
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1d")
        return df is not None and not df.empty
    except Exception:
        return False


def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Append core technical indicators to historical OHLCV data:
    - Moving averages (SMA7, SMA21, SMA50)
    - Exponential averages (EMA12, EMA26)
    - Relative Strength Index (RSI14)
    - MACD and Signal Lines
    - Bollinger Bands (20-day, 2 Standard Deviations)
    """
    df = df.copy()
    if df.empty or len(df) < 2:
        return df

    close = df["Close"]

    # Moving Averages
    df["SMA7"] = close.rolling(7).mean()
    df["SMA21"] = close.rolling(21).mean()
    df["SMA50"] = close.rolling(50).mean()

    # EMAs
    df["EMA12"] = close.ewm(span=12, adjust=False).mean()
    df["EMA26"] = close.ewm(span=26, adjust=False).mean()

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    df["RSI14"] = 100 - (100 / (1 + rs))

    # MACD
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    # Bollinger Bands
    df["BB_Mid"] = close.rolling(20).mean()
    df["BB_Std"] = close.rolling(20).std()
    df["BB_Upper"] = df["BB_Mid"] + (2 * df["BB_Std"])
    df["BB_Lower"] = df["BB_Mid"] - (2 * df["BB_Std"])

    return df
