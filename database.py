"""
database.py — SQLite3 Data Access Layer
Stock Portfolio Analyzer
"""

import sqlite3
import os
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), "portfolio.db")


def get_connection():
    """
    ✅ FIX: Added error handling for connection failures
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        raise


def init_db():
    """
    ✅ FIX: Added try/finally to ensure connection is always closed
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                symbol      TEXT PRIMARY KEY,
                company     TEXT NOT NULL,
                sector      TEXT DEFAULT 'Unknown',
                exchange    TEXT DEFAULT 'NSE'
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol      TEXT NOT NULL,
                txn_type    TEXT NOT NULL CHECK(txn_type IN ('BUY','SELL')),
                quantity    REAL NOT NULL CHECK(quantity > 0),
                price       REAL NOT NULL CHECK(price > 0),
                brokerage   REAL DEFAULT 0 CHECK(brokerage >= 0),
                date        TEXT NOT NULL,
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol       TEXT NOT NULL,
                company      TEXT,
                target_price REAL NOT NULL CHECK(target_price > 0),
                added_date   TEXT,
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS dividends (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol              TEXT NOT NULL,
                amount_per_share    REAL NOT NULL CHECK(amount_per_share >= 0),
                quantity            REAL NOT NULL CHECK(quantity > 0),
                date                TEXT NOT NULL,
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS price_cache (
                symbol      TEXT PRIMARY KEY,
                ltp         REAL,
                high        REAL,
                low         REAL,
                prev_close  REAL,
                volume      REAL,
                updated     TEXT,
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """)

        # Default admin
        pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT OR IGNORE INTO admin VALUES (?, ?)", ("admin", pwd_hash))

        conn.commit()
        print("Database initialized successfully.")

    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# ── Stocks ──────────────────────────────────────────────────────────────────

def add_stock(symbol, company, sector="Unknown", exchange="NSE"):
    """
    ✅ FIX: Added error handling and improved exception handling
    """
    conn = None
    try:
        conn = get_connection()
        conn.execute(
            "INSERT OR IGNORE INTO stocks VALUES (?,?,?,?)",
            (symbol.upper(), company, sector, exchange)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error adding stock {symbol}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def get_all_stocks():
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM stocks ORDER BY symbol").fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"Error retrieving stocks: {e}")
        return []
    finally:
        if conn:
            conn.close()


def delete_stock(symbol):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        conn.execute("DELETE FROM stocks WHERE symbol=?", (symbol.upper(),))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error deleting stock {symbol}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# ── Transactions ─────────────────────────────────────────────────────────────

def add_transaction(symbol, txn_type, quantity, price, brokerage, date):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO transactions (symbol,txn_type,quantity,price,brokerage,date) VALUES (?,?,?,?,?,?)",
            (symbol.upper(), txn_type, quantity, price, brokerage, date)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error adding transaction for {symbol}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def get_transactions(symbol=None):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        if symbol:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE symbol=? ORDER BY date DESC", (symbol.upper(),)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM transactions ORDER BY date DESC").fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"Error retrieving transactions: {e}")
        return []
    finally:
        if conn:
            conn.close()


def delete_transaction(txn_id):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        conn.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error deleting transaction {txn_id}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def get_holdings():
    """
    Returns net holdings: symbol → {qty, avg_cost, invested}

    Calculation:
    - qty: Net quantity after buys and sells
    - avg_cost: Total buy cost / total buy quantity (per share)
    - invested: Current holdings * avg_cost (cost basis of remaining shares)

    ✅ FIX: Added error handling
    """
    conn = None
    try:
        conn = get_connection()
        rows = conn.execute("""
            SELECT symbol,
                   SUM(CASE WHEN txn_type='BUY' THEN quantity ELSE -quantity END) AS net_qty,
                   SUM(CASE WHEN txn_type='BUY' THEN quantity*(price+brokerage/quantity) ELSE 0 END) AS total_cost,
                   SUM(CASE WHEN txn_type='BUY' THEN quantity ELSE 0 END) AS total_buy_qty
            FROM transactions
            GROUP BY symbol
            HAVING net_qty > 0.001
        """).fetchall()

        holdings = {}
        for sym, qty, cost, buy_qty in rows:
            # ✅ FIX: Improved division by zero check
            if buy_qty and buy_qty > 0:
                avg = cost / buy_qty
            else:
                avg = 0
            holdings[sym] = {"qty": qty, "avg_cost": avg, "invested": qty * avg}
        return holdings

    except sqlite3.Error as e:
        print(f"Error retrieving holdings: {e}")
        return {}
    finally:
        if conn:
            conn.close()


# ── Watchlist ────────────────────────────────────────────────────────────────

def add_watchlist(symbol, company, target_price, date):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO watchlist (symbol,company,target_price,added_date) VALUES (?,?,?,?)",
            (symbol.upper(), company, target_price, date)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error adding to watchlist {symbol}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def get_watchlist():
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM watchlist ORDER BY symbol").fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"Error retrieving watchlist: {e}")
        return []
    finally:
        if conn:
            conn.close()


def delete_watchlist(wl_id):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        conn.execute("DELETE FROM watchlist WHERE id=?", (wl_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error deleting watchlist item {wl_id}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# ── Dividends ────────────────────────────────────────────────────────────────

def add_dividend(symbol, amount_per_share, quantity, date):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO dividends (symbol,amount_per_share,quantity,date) VALUES (?,?,?,?)",
            (symbol.upper(), amount_per_share, quantity, date)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error adding dividend for {symbol}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def get_dividends(symbol=None):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        if symbol:
            rows = conn.execute(
                "SELECT * FROM dividends WHERE symbol=? ORDER BY date DESC", (symbol.upper(),)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM dividends ORDER BY date DESC").fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"Error retrieving dividends: {e}")
        return []
    finally:
        if conn:
            conn.close()


def delete_dividend(div_id):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        conn.execute("DELETE FROM dividends WHERE id=?", (div_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error deleting dividend {div_id}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# ── Price Cache ──────────────────────────────────────────────────────────────

def update_price_cache(symbol, ltp, high, low, prev_close, volume, updated):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        conn = get_connection()
        conn.execute("""
            INSERT INTO price_cache VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(symbol) DO UPDATE SET
                ltp=excluded.ltp, high=excluded.high, low=excluded.low,
                prev_close=excluded.prev_close, volume=excluded.volume, updated=excluded.updated
        """, (symbol.upper(), ltp, high, low, prev_close, volume, updated))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error updating price cache for {symbol}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def get_price_cache():
    """
    ✅ FIX: Added error handling and improved dict comprehension safety
    """
    conn = None
    try:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM price_cache").fetchall()

        # ✅ FIX: Safe dict construction with proper error handling
        cache = {}
        for r in rows:
            try:
                cache[r[0]] = {
                    "ltp": r[1],
                    "high": r[2],
                    "low": r[3],
                    "prev_close": r[4],
                    "volume": r[5],
                    "updated": r[6]
                }
            except (IndexError, TypeError) as e:
                print(f"Error processing price cache row for {r[0]}: {e}")
                continue

        return cache
    except sqlite3.Error as e:
        print(f"Error retrieving price cache: {e}")
        return {}
    finally:
        if conn:
            conn.close()


# ── Admin ────────────────────────────────────────────────────────────────────

def verify_admin(username, password):
    """✅ FIX: Added error handling"""
    conn = None
    try:
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_connection()
        row = conn.execute(
            "SELECT 1 FROM admin WHERE username=? AND password=?", (username, pwd_hash)
        ).fetchone()
        return row is not None
    except sqlite3.Error as e:
        print(f"Error verifying admin credentials: {e}")
        return False
    finally:
        if conn:
            conn.close()
