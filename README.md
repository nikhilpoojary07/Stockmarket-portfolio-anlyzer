# 📈 Stock Portfolio Analyzer

A full-featured desktop application for managing your stock portfolio — built with
**Python · Tkinter · SQLite3 · Matplotlib · yfinance · scikit-learn**.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
python main.py
```

### 3. Open in PyCharm
- Open the `StockPortfolioAnalyzer/` folder as a project
- Right-click `main.py` → **Run 'main'**

---

## 📦 Project Structure

```
StockPortfolioAnalyzer/
├── main.py           ← Application entry point (Tkinter GUI)
├── database.py       ← SQLite3 data access layer (CRUD)
├── price_fetcher.py  ← yfinance live price fetching + offline cache
├── predictor.py      ← 🤖 ML prediction model (Linear Regression)
├── exporter.py       ← CSV export utility
├── requirements.txt  ← Python package dependencies
├── README.md         ← This file
└── portfolio.db      ← Auto-created SQLite3 database on first run
```

---

## 🗂 Modules Overview

| Module | Purpose |
|---|---|
| `main.py` | Tkinter GUI — all 6 tabs, charts, theme toggle |
| `database.py` | SQLite3 CRUD — stocks, transactions, watchlist, dividends, price_cache, admin |
| `price_fetcher.py` | Fetches live prices via yfinance; offline fallback to cache |
| `predictor.py` | Trains a Linear Regression model on technical indicators to forecast price |
| `exporter.py` | Export holdings / transactions to CSV |

---

## 🤖 Prediction Model

The **Prediction Tab** trains a `LinearRegression` model on 2 years of daily OHLCV data.

**Features used:**
- MA7, MA21, MA50 (Moving Averages)
- RSI (Relative Strength Index, 14-day)
- MOM10 (10-day Momentum)
- VOL10 (10-day Rolling Volatility)

**Output:**
- Predicted closing price N days ahead
- Direction: UP / DOWN / FLAT
- Confidence score (%)
- Back-test MAPE (Mean Absolute Percentage Error)
- Forecast chart overlaid on historical data

---

## 🔑 Admin Login

Default credentials:
- **Username:** `admin`
- **Password:** `admin123`

---

## 📊 Tabs

| Tab | Features |
|---|---|
| **Holdings** | Live table with LTP, P&L, Day Gain |
| **Transactions** | Add/delete BUY/SELL entries |
| **Watchlist** | Target price tracking with gap % |
| **Dividends** | Log dividend income, view total yield |
| **Analytics** | Pie, Bar, NAV Line, Sector charts |
| **📊 Prediction** | ML price forecast with confidence score |

---

## 🌐 Symbols

Use NSE format (e.g., `RELIANCE`, `TCS`, `INFY`).  
The app auto-appends `.NS` for Yahoo Finance API calls.

For US stocks use full tickers: `AAPL`, `MSFT`, etc.

---

## ⚠ Disclaimer

This tool is for **educational purposes only**.  
Price predictions are based on historical patterns and are **not financial advice**.
