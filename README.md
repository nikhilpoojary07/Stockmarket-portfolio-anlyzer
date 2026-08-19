 Stock Portfolio Analyzer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite
![Machine Learning](https://img.shields.io/badge/ML-scikit--learn-F7931E?logo=scikitlearn)
![Matplotlib](https://img.shields.io/badge/Charts-Matplotlib-blue)
![License](https://img.shields.io/badge/License-MIT-red)

A Python desktop application for managing stock portfolios, tracking live market prices, visualizing investment performance, and forecasting future prices using Machine Learning.




**Stock Portfolio Analyzer** is a desktop-based investment management system developed using **Python** and **Tkinter**. It helps users organize stock holdings, monitor portfolio performance, analyze investments through interactive charts, and predict future stock prices using Machine Learning.
s

- 📈 Live Stock Price Tracking
- 💼 Portfolio Management
- 📊 Interactive Analytics Dashboard
- 🤖 Machine Learning Price Prediction
- ⭐ Watchlist Management
- 💰 Dividend Tracking
- 📤 CSV Export
- 🌙 Dark/Light Theme Support
- 💾 Offline Price Cache

---

# 🚀 Features

## 📊 Portfolio Management

- Add, edit, and delete stock holdings
- Automatic Profit & Loss calculation
- Live Market Value
- Daily Gain/Loss tracking
- Portfolio Summary

---
 Live Market Data

Live stock prices are fetched using **Yahoo Finance**.

Supported Markets:

- 🇮🇳 NSE (India)
- 🇺🇸 US Stock Market

Example Symbols

```
RELIANCE
INFY
TCS
SBIN

AAPL
MSFT
NVDA
GOOGL
```

---

## 📈 Analytics Dashboard

Visualize your portfolio using interactive charts.

Available Charts

- Portfolio Allocation
- Profit vs Investment
- Sector Distribution
- NAV Trend
- Holdings Distribution
- Performance Analysis

Powered by **Matplotlib**.

---

## ⭐ Watchlist

Monitor stocks before investing.

Features

- Live Prices
- Target Price
- Gap Percentage
- Quick Tracking

---

## 💰 Dividend Manager

Track passive income from dividends.

Features

- Record Dividend Payments
- View Dividend History
- Calculate Total Dividend Income
- Dividend Yield Analysis

---

# 🤖 Machine Learning Prediction

The application predicts future stock prices using **Scikit-learn Linear Regression** trained on two years of historical market data.

### Technical Indicators Used

- Moving Average (7 Days)
- Moving Average (21 Days)
- Moving Average (50 Days)
- RSI (14)
- Momentum (10 Days)
- Rolling Volatility

### Prediction Output

- Predicted Future Price
- Market Direction
- Confidence Score
- MAPE Accuracy
- Historical vs Predicted Graph

---

# 🗂 Project Structure

```
StockPortfolioAnalyzer/
│
├── main.py
├── database.py
├── price_fetcher.py
├── predictor.py
├── exporter.py
├── requirements.txt
├── README.md
└── portfolio.db
```

---

# 🧩 Modules

| Module | Description |
|---------|-------------|
| **main.py** | Tkinter-based desktop application |
| **database.py** | SQLite CRUD operations |
| **price_fetcher.py** | Live stock prices with offline caching |
| **predictor.py** | ML-based stock prediction module |
| **exporter.py** | Export portfolio data to CSV |

---

# 🖥 Application Tabs

| Tab | Description |
|------|-------------|
| 📁 Holdings | Portfolio holdings with live prices |
| 💳 Transactions | BUY / SELL history |
| ⭐ Watchlist | Favorite stocks with target tracking |
| 💰 Dividends | Dividend records and earnings |
| 📊 Analytics | Charts and portfolio insights |
| 🤖 Prediction | Machine Learning stock forecasting |

---

# ⚙ Installation

## Clone Repository

```bash
git clone https://github.com/your-username/StockPortfolioAnalyzer.git
```

```
cd StockPortfolioAnalyzer
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run the Application

```bash
python main.py
```

---

# 📦 Requirements

- Python 3.10+
- Tkinter
- SQLite3
- Pandas
- NumPy
- Matplotlib
- yfinance
- scikit-learn

Install manually if required:

```bash
pip install pandas numpy matplotlib yfinance scikit-learn
```

---

# 📈 Machine Learning Workflow

```
Historical Data
        │
        ▼
Data Cleaning
        │
        ▼
Feature Engineering
        │
        ▼
Linear Regression Model
        │
        ▼
Future Price Prediction
        │
        ▼
Visualization
```

---

# 🔐 Admin Login

Default Credentials

| Username | Password |
|----------|----------|
| admin | admin123 |

> **Note:** Change the default credentials before using the application in a production environment.

---

# 🌍 Supported Stock Symbols

### Indian Stocks (NSE)

```
RELIANCE
INFY
TCS
SBIN
HDFCBANK
ICICIBANK
```

The application automatically converts them to:

```
RELIANCE.NS
INFY.NS
```

### US Stocks

```
AAPL
MSFT
NVDA
GOOGL
META
AMZN
```

---

# 📸 Screenshots

Create a folder named **screenshots/**

```
screenshots/
├── dashboard.png
├── holdings.png
├── analytics.png
├── prediction.png
├── watchlist.png
└── dividends.png
```

Then include:

```markdown
## Dashboard

![Dashboard](screenshots/dashboard.png)

## Analytics

![Analytics](screenshots/analytics.png)

## Prediction

![Prediction](screenshots/prediction.png)
```

---

# 🚀 Future Improvements

- LSTM & XGBoost Prediction Models
- Risk Analysis
- Sharpe Ratio
- Monte Carlo Simulation
- Email Price Alerts
- News Sentiment Analysis
- Candlestick Charts
- Multi-user Authentication
- Cloud Database Support
- Mobile Companion App

---

# 🛠 Technology Stack

| Category | Technology |
|----------|------------|
| Language | Python |
| GUI | Tkinter |
| Database | SQLite3 |
| Machine Learning | Scikit-learn |
| Data Processing | Pandas & NumPy |
| Visualization | Matplotlib |
| Market Data | Yahoo Finance (yfinance) |

---

# 🤝 Contributing

Contributions are welcome!

1. Fork this repository.
2. Create a new feature branch.
3. Commit your changes.
4. Push the branch.
5. Open a Pull Request.

---

# 📄 License

This project is licensed under the **MIT License**.

---

# ⚠ Disclaimer

This application is intended for **educational and learning purposes only**.

The stock prices are obtained from Yahoo Finance, and predictions are generated using historical data with machine learning models. They **should not be interpreted as financial or investment advice**.

Always perform your own research before making investment decisions.

---

<div align="center">

### ⭐ If you found this project useful, please give it a Star!

**Made with ❤️ using Python**

</div>
