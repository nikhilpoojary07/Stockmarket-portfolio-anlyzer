"""
exporter.py — CSV Export Utility
Stock Portfolio Analyzer
"""

import csv
import os
import datetime
import database as db


def export_holdings(filepath: str = None) -> str:
    """
    Export current holdings to CSV file.

    Args:
        filepath: Output file path. If None, generates timestamped filename.

    Returns:
        The filepath where the CSV was saved.

    Raises:
        IOError: If file cannot be written.
        ValueError: If no holdings data available.

    ✅ FIX: Added error handling, validation, and defensive programming
    """
    try:
        # ✅ FIX: Get holdings and cache with error handling
        holdings = db.get_holdings()
        if not holdings:
            raise ValueError("No holdings data available to export.")

        cache = db.get_price_cache() or {}

        # ✅ FIX: Generate filepath if not provided
        if not filepath:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(os.path.dirname(__file__), f"holdings_{ts}.csv")

        # ✅ FIX: Validate filepath is valid and directory exists
        filepath = os.path.abspath(filepath)
        directory = os.path.dirname(filepath)

        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        if os.path.exists(filepath):
            print(f"[WARNING] File already exists, will be overwritten: {filepath}")

        # ✅ FIX: Construct rows with proper error handling per row
        rows = []
        for sym, h in holdings.items():
            try:
                # ✅ FIX: Safe cache access
                price_info = cache.get(sym, {})
                if not isinstance(price_info, dict):
                    price_info = {}

                ltp = float(price_info.get("ltp", 0))
                cur_val = h["qty"] * ltp
                pnl = cur_val - h["invested"]
                pnl_pct = (pnl / h["invested"] * 100) if h["invested"] else 0

                rows.append({
                    "Symbol": sym,
                    "Qty": round(h["qty"], 2),
                    "Avg Cost": round(h["avg_cost"], 2),
                    "Invested": round(h["invested"], 2),
                    "LTP": round(ltp, 2),
                    "Current Value": round(cur_val, 2),
                    "P&L": round(pnl, 2),
                    "P&L %": round(pnl_pct, 2),
                })
            except (KeyError, TypeError, ValueError) as e:
                print(f"[WARNING] Error processing {sym}: {e}. Skipping this holding.")
                continue

        # ✅ FIX: Handle case where all rows failed to process
        if not rows:
            raise ValueError("Could not process any holdings data.")

        # ✅ FIX: Write CSV with proper error handling
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                fieldnames = rows[0].keys() if rows else []
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            print(f"[SUCCESS] Exported {len(rows)} holdings to: {filepath}")
            return filepath

        except IOError as e:
            raise IOError(f"Failed to write CSV file {filepath}: {e}")

    except (ValueError, IOError) as e:
        print(f"[ERROR] Export failed: {e}")
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error during export: {e}")
        raise


def export_transactions(filepath: str = None) -> str:
    """
    Export all transactions to CSV file.

    Args:
        filepath: Output file path. If None, generates timestamped filename.

    Returns:
        The filepath where the CSV was saved.

    Raises:
        IOError: If file cannot be written.
        ValueError: If no transactions available.

    ✅ FIX: Added error handling, validation, and defensive programming
    """
    try:
        # ✅ FIX: Get transactions with error handling
        txns = db.get_transactions()
        if not txns:
            raise ValueError("No transactions data available to export.")

        # ✅ FIX: Generate filepath if not provided
        if not filepath:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(os.path.dirname(__file__), f"transactions_{ts}.csv")

        # ✅ FIX: Validate filepath and ensure directory exists
        filepath = os.path.abspath(filepath)
        directory = os.path.dirname(filepath)

        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        if os.path.exists(filepath):
            print(f"[WARNING] File already exists, will be overwritten: {filepath}")

        # ✅ FIX: Validate transaction data before writing
        header = ["ID", "Symbol", "Type", "Qty", "Price", "Brokerage", "Date"]

        # ✅ FIX: Validate each row has correct number of columns
        valid_txns = []
        for txn in txns:
            try:
                if len(txn) < len(header):
                    print(f"[WARNING] Skipping malformed transaction: {txn}")
                    continue
                valid_txns.append(txn[:len(header)])  # Take only the expected columns
            except Exception as e:
                print(f"[WARNING] Error processing transaction {txn}: {e}")
                continue

        if not valid_txns:
            raise ValueError("Could not process any transaction data.")

        # ✅ FIX: Write CSV with proper error handling
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(valid_txns)

            print(f"[SUCCESS] Exported {len(valid_txns)} transactions to: {filepath}")
            return filepath

        except IOError as e:
            raise IOError(f"Failed to write CSV file {filepath}: {e}")

    except (ValueError, IOError) as e:
        print(f"[ERROR] Export failed: {e}")
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error during export: {e}")
        raise


def export_dividends(filepath: str = None) -> str:
    """
    Export all dividends to CSV file.

    Args:
        filepath: Output file path. If None, generates timestamped filename.

    Returns:
        The filepath where the CSV was saved.

    ✅ FIX: Added new function for exporter completeness
    """
    try:
        dividends = db.get_dividends()
        if not dividends:
            raise ValueError("No dividends data available to export.")

        if not filepath:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(os.path.dirname(__file__), f"dividends_{ts}.csv")

        filepath = os.path.abspath(filepath)
        directory = os.path.dirname(filepath)

        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        if os.path.exists(filepath):
            print(f"[WARNING] File already exists, will be overwritten: {filepath}")

        header = ["ID", "Symbol", "Amount Per Share", "Quantity", "Date"]

        valid_divs = []
        for div in dividends:
            try:
                if len(div) < len(header):
                    print(f"[WARNING] Skipping malformed dividend: {div}")
                    continue
                valid_divs.append(div[:len(header)])
            except Exception as e:
                print(f"[WARNING] Error processing dividend {div}: {e}")
                continue

        if not valid_divs:
            raise ValueError("Could not process any dividend data.")

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(valid_divs)

            print(f"[SUCCESS] Exported {len(valid_divs)} dividends to: {filepath}")
            return filepath

        except IOError as e:
            raise IOError(f"Failed to write CSV file {filepath}: {e}")

    except (ValueError, IOError) as e:
        print(f"[ERROR] Export failed: {e}")
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error during export: {e}")
        raise


def export_watchlist(filepath: str = None) -> str:
    """
    Export watchlist to CSV file.

    Args:
        filepath: Output file path. If None, generates timestamped filename.

    Returns:
        The filepath where the CSV was saved.

    ✅ FIX: Added new function for exporter completeness
    """
    try:
        watchlist = db.get_watchlist()
        if not watchlist:
            raise ValueError("No watchlist data available to export.")

        if not filepath:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(os.path.dirname(__file__), f"watchlist_{ts}.csv")

        filepath = os.path.abspath(filepath)
        directory = os.path.dirname(filepath)

        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        if os.path.exists(filepath):
            print(f"[WARNING] File already exists, will be overwritten: {filepath}")

        header = ["ID", "Symbol", "Company", "Target Price", "Added Date"]

        valid_wl = []
        for wl in watchlist:
            try:
                if len(wl) < len(header):
                    print(f"[WARNING] Skipping malformed watchlist item: {wl}")
                    continue
                valid_wl.append(wl[:len(header)])
            except Exception as e:
                print(f"[WARNING] Error processing watchlist item {wl}: {e}")
                continue

        if not valid_wl:
            raise ValueError("Could not process any watchlist data.")

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(valid_wl)

            print(f"[SUCCESS] Exported {len(valid_wl)} watchlist items to: {filepath}")
            return filepath

        except IOError as e:
            raise IOError(f"Failed to write CSV file {filepath}: {e}")

    except (ValueError, IOError) as e:
        print(f"[ERROR] Export failed: {e}")
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error during export: {e}")
        raise
