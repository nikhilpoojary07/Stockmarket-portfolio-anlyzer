"""
predictor.py — Stock Price Prediction Model
Uses Linear Regression + Moving Averages + RSI as features.
Returns a short-term (7-day / 30-day) price forecast with confidence.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.metrics import mean_absolute_percentage_error

    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

import price_fetcher


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer technical features for the ML model."""
    df = df.copy()
    close = df["Close"].squeeze()

    df["MA7"] = close.rolling(7).mean()
    df["MA21"] = close.rolling(21).mean()
    df["MA50"] = close.rolling(50).mean()

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    # Momentum & volatility
    df["MOM10"] = close.pct_change(10)
    df["VOL10"] = close.rolling(10).std()
    df["TARGET"] = close.shift(-1)  # next-day close (label)

    df.dropna(inplace=True)
    return df


def _is_valid_features(row: pd.Series) -> bool:
    """
    ✅ FIX: Check if a row has valid (non-NaN, non-Inf) feature values
    """
    features = ["MA7", "MA21", "MA50", "RSI", "MOM10", "VOL10"]
    for feat in features:
        try:
            val = float(row[feat])
            if np.isnan(val) or np.isinf(val):
                return False
        except (KeyError, TypeError, ValueError):
            return False
    return True


def predict(symbol: str, days_ahead: int = 7) -> dict:
    """
    Train a LinearRegression model on 1 year of daily data and
    predict the closing price `days_ahead` trading days into the future.

    Returns:
        {
          "symbol": str,
          "current_price": float,
          "predicted_price": float,
          "predicted_date": str,
          "direction": "UP" | "DOWN" | "FLAT",
          "confidence": float (0-100),
          "mape": float,                   # back-test error %
          "forecast_series": [(date_str, price), ...],
          "ma7": float, "ma21": float, "rsi": float,
          "error": str | None
        }
    """
    result = {
        "symbol": symbol, "current_price": 0, "predicted_price": 0,
        "predicted_date": "", "direction": "FLAT", "confidence": 0,
        "mape": 0, "forecast_series": [], "ma7": 0, "ma21": 0, "rsi": 0,
        "error": None
    }

    if not SKLEARN_OK:
        result["error"] = "scikit-learn not installed. Run: pip install scikit-learn"
        return result

    # ✅ FIX: Wrap entire function in try/except to catch all errors
    try:
        df_raw = price_fetcher.fetch_history(symbol, period="2y")
        if df_raw is None or len(df_raw) < 60:
            result["error"] = "Insufficient historical data (need ≥ 60 days)."
            return result

        df = _add_features(df_raw)
        if len(df) < 40:
            result["error"] = "Not enough data after feature engineering."
            return result

        features = ["MA7", "MA21", "MA50", "RSI", "MOM10", "VOL10"]
        X = df[features].values
        y = df["TARGET"].values

        # Train/test split (80/20)
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        scaler = MinMaxScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = LinearRegression()
        model.fit(X_train_s, y_train)

        y_pred_test = model.predict(X_test_s)
        mape = mean_absolute_percentage_error(y_test, y_pred_test) * 100

        # Current indicators
        last_row = df.iloc[-1]

        # ✅ FIX: Proper Series access instead of assuming DataFrame structure
        close_series = df_raw["Close"]
        if isinstance(close_series, pd.Series):
            current_price = float(close_series.iloc[-1])
        else:
            # Fallback for unexpected structure
            current_price = float(close_series.values[-1])

        result["current_price"] = round(current_price, 2)
        result["ma7"] = round(float(last_row["MA7"]), 2)
        result["ma21"] = round(float(last_row["MA21"]), 2)
        result["rsi"] = round(float(last_row["RSI"]), 2)
        result["mape"] = round(mape, 2)

        # Rolling forecast for `days_ahead` steps
        forecast_series = []
        sim_df = df.copy()

        for i in range(days_ahead):
            last = sim_df.iloc[-1]

            # ✅ FIX: Validate features before prediction
            if not _is_valid_features(last):
                result["error"] = f"Invalid features at step {i}. Contains NaN or Inf values."
                return result

            x_input = np.array([[last["MA7"], last["MA21"], last["MA50"],
                                 last["RSI"], last["MOM10"], last["VOL10"]]])

            # ✅ FIX: Bound-check scaled features to prevent extreme predictions
            x_scaled = scaler.transform(x_input)
            x_scaled = np.clip(x_scaled, -10, 10)  # Reasonable bounds

            next_price = float(model.predict(x_scaled)[0])

            # ✅ FIX: Validate predicted price is reasonable
            if np.isnan(next_price) or np.isinf(next_price):
                result["error"] = f"Invalid prediction at step {i}. Got NaN or Inf."
                return result

            # Simulate next row for rolling features
            next_date = (sim_df.index[-1] + timedelta(days=1)).strftime("%Y-%m-%d")
            forecast_series.append((next_date, round(next_price, 2)))

            # Append synthetic row with proper error handling
            try:
                # ✅ FIX: Proper Volume access using try/except
                try:
                    volume = float(last_row["Volume"])
                except (KeyError, TypeError, ValueError):
                    volume = 0.0

                new_row = pd.DataFrame({
                    "Close": [next_price], "High": [next_price * 1.005],
                    "Low": [next_price * 0.995], "Open": [next_price],
                    "Volume": [volume]
                }, index=[sim_df.index[-1] + timedelta(days=1)])

                sim_close = pd.concat([sim_df["Close"], new_row["Close"]], ignore_index=False)

                # ✅ FIX: Recalculate features with proper error handling
                ma7_val = sim_close.rolling(7).mean().iloc[-1]
                ma21_val = sim_close.rolling(21).mean().iloc[-1]
                ma50_val = sim_close.rolling(50).mean().iloc[-1]

                # Recalculate RSI
                delta = sim_close.diff()
                gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
                loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
                rs_val = gain / (loss + 1e-9)
                rsi_val = 100 - (100 / (1 + rs_val))

                mom_val = sim_close.pct_change(10).iloc[-1]
                vol_val = sim_close.rolling(10).std().iloc[-1]

                # ✅ FIX: Check for NaN/Inf in calculated features
                if any(np.isnan([ma7_val, ma21_val, ma50_val, rsi_val, mom_val, vol_val])) or \
                        any(np.isinf([ma7_val, ma21_val, ma50_val, rsi_val, mom_val, vol_val])):
                    # Use previous values if calculation failed
                    ma7_val = float(last["MA7"]) if not np.isnan(float(last["MA7"])) else 0
                    ma21_val = float(last["MA21"]) if not np.isnan(float(last["MA21"])) else 0
                    ma50_val = float(last["MA50"]) if not np.isnan(float(last["MA50"])) else 0
                    rsi_val = float(last["RSI"]) if not np.isnan(float(last["RSI"])) else 50
                    mom_val = float(last["MOM10"]) if not np.isnan(float(last["MOM10"])) else 0
                    vol_val = float(last["VOL10"]) if not np.isnan(float(last["VOL10"])) else 0

                new_sim_row = pd.DataFrame({
                    "Close": [next_price], "MA7": [ma7_val], "MA21": [ma21_val],
                    "MA50": [ma50_val], "RSI": [rsi_val], "MOM10": [mom_val],
                    "VOL10": [vol_val], "TARGET": [next_price]
                }, index=[sim_df.index[-1] + timedelta(days=1)])

                sim_df = pd.concat([sim_df, new_sim_row], ignore_index=False)

            except Exception as e:
                result["error"] = f"Error simulating step {i}: {str(e)}"
                return result

        if not forecast_series:
            result["error"] = "No forecast generated."
            return result

        final_price = forecast_series[-1][1]
        final_date = forecast_series[-1][0]

        change_pct = ((final_price - current_price) / current_price) * 100 if current_price > 0 else 0
        direction = "UP" if change_pct > 0.5 else ("DOWN" if change_pct < -0.5 else "FLAT")

        # Confidence: inversely proportional to MAPE (capped 0-95)
        confidence = max(0, min(95, round(100 - mape * 2, 1)))

        result.update({
            "predicted_price": round(final_price, 2),
            "predicted_date": final_date,
            "direction": direction,
            "confidence": confidence,
            "forecast_series": forecast_series,
            "change_pct": round(change_pct, 2),
        })

    except Exception as e:
        # ✅ FIX: Catch any unexpected errors
        result["error"] = f"Prediction error: {str(e)}"
        print(f"[ERROR] {symbol} prediction failed: {e}")

    return result
