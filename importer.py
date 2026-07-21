"""
importer.py — CSV Import Utility
Stock Portfolio Analyzer

Handles importing transactions, watchlist, and dividends from CSV files.
"""

import csv
import os
from datetime import datetime
import database as db


class CSVImporter:
    """Handles CSV import for transactions, watchlist, and dividends."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.imported_count = 0
        self.skipped_count = 0
    
    def reset_counters(self):
        """Reset error, warning, and count trackers."""
        self.errors = []
        self.warnings = []
        self.imported_count = 0
        self.skipped_count = 0
    
    def validate_date(self, date_str):
        """Validate and parse date in YYYY-MM-DD format."""
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None
    
    def import_transactions(self, filepath):
        """
        Import transactions from CSV.
        Expected columns: Symbol, Type, Quantity, Price, Brokerage, Date
        """
        self.reset_counters()
        
        if not os.path.exists(filepath):
            self.errors.append(f"File not found: {filepath}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if not reader.fieldnames:
                    self.errors.append("CSV file is empty or invalid")
                    return False
                
                # Validate headers
                required_cols = {'Symbol', 'Type', 'Quantity', 'Price', 'Brokerage', 'Date'}
                csv_cols = set(col.strip() for col in reader.fieldnames)
                
                if not required_cols.issubset(csv_cols):
                    missing = required_cols - csv_cols
                    self.errors.append(f"Missing columns: {', '.join(missing)}")
                    return False
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        symbol = row['Symbol'].strip().upper()
                        txn_type = row['Type'].strip().upper()
                        quantity_str = row['Quantity'].strip()
                        price_str = row['Price'].strip()
                        brokerage_str = row['Brokerage'].strip()
                        date_str = row['Date'].strip()
                        
                        # Validate required fields
                        if not symbol:
                            self.errors.append(f"Row {row_num}: Symbol is empty")
                            self.skipped_count += 1
                            continue
                        
                        if txn_type not in ('BUY', 'SELL'):
                            self.errors.append(f"Row {row_num}: Invalid Type '{txn_type}'. Use BUY or SELL")
                            self.skipped_count += 1
                            continue
                        
                        # Parse numeric fields
                        try:
                            quantity = float(quantity_str)
                            price = float(price_str)
                            brokerage = float(brokerage_str) if brokerage_str else 0.0
                        except ValueError as e:
                            self.errors.append(f"Row {row_num}: Invalid number format - {str(e)}")
                            self.skipped_count += 1
                            continue
                        
                        if quantity <= 0:
                            self.errors.append(f"Row {row_num}: Quantity must be positive")
                            self.skipped_count += 1
                            continue
                        
                        if price <= 0:
                            self.errors.append(f"Row {row_num}: Price must be positive")
                            self.skipped_count += 1
                            continue
                        
                        # Validate date
                        parsed_date = self.validate_date(date_str)
                        if not parsed_date:
                            self.errors.append(f"Row {row_num}: Invalid date format '{date_str}'. Use YYYY-MM-DD")
                            self.skipped_count += 1
                            continue
                        
                        # Auto-create stock if doesn't exist
                        try:
                            db.add_stock(symbol, f"Stock - {symbol}", "Unknown", "NSE")
                        except Exception:
                            pass  # Stock might already exist
                        
                        # Insert transaction
                        db.add_transaction(symbol, txn_type, quantity, price, brokerage, parsed_date)
                        self.imported_count += 1
                        
                    except Exception as e:
                        self.errors.append(f"Row {row_num}: {str(e)}")
                        self.skipped_count += 1
                        continue
            
            return True
        
        except Exception as e:
            self.errors.append(f"Error reading file: {str(e)}")
            return False
    
    def import_watchlist(self, filepath):
        """
        Import watchlist from CSV.
        Expected columns: Symbol, Company, Target Price, Date Added
        """
        self.reset_counters()
        
        if not os.path.exists(filepath):
            self.errors.append(f"File not found: {filepath}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if not reader.fieldnames:
                    self.errors.append("CSV file is empty or invalid")
                    return False
                
                # Validate headers
                required_cols = {'Symbol', 'Company', 'Target Price', 'Date Added'}
                csv_cols = set(col.strip() for col in reader.fieldnames)
                
                if not required_cols.issubset(csv_cols):
                    missing = required_cols - csv_cols
                    self.errors.append(f"Missing columns: {', '.join(missing)}")
                    return False
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        symbol = row['Symbol'].strip().upper()
                        company = row['Company'].strip()
                        target_price_str = row['Target Price'].strip()
                        date_str = row['Date Added'].strip()
                        
                        # Validate required fields
                        if not symbol:
                            self.errors.append(f"Row {row_num}: Symbol is empty")
                            self.skipped_count += 1
                            continue
                        
                        if not company:
                            company = f"Company - {symbol}"
                        
                        # Parse numeric field
                        try:
                            target_price = float(target_price_str)
                        except ValueError:
                            self.errors.append(f"Row {row_num}: Invalid Target Price format")
                            self.skipped_count += 1
                            continue
                        
                        if target_price <= 0:
                            self.errors.append(f"Row {row_num}: Target Price must be positive")
                            self.skipped_count += 1
                            continue
                        
                        # Validate date
                        parsed_date = self.validate_date(date_str)
                        if not parsed_date:
                            self.errors.append(f"Row {row_num}: Invalid date format '{date_str}'. Use YYYY-MM-DD")
                            self.skipped_count += 1
                            continue
                        
                        # Auto-create stock if doesn't exist (prevents FOREIGN KEY constraint)
                        try:
                            db.add_stock(symbol, company or f"Stock - {symbol}", "Unknown", "NSE")
                        except Exception:
                            pass  # Stock might already exist
                        
                        # Insert watchlist entry
                        try:
                            db.add_watchlist(symbol, company, target_price, parsed_date)
                            self.imported_count += 1
                        except Exception as fk_error:
                            # Handle FOREIGN KEY constraint errors
                            if "FOREIGN KEY" in str(fk_error):
                                self.errors.append(f"Row {row_num}: Stock '{symbol}' not found. Created automatically.")
                            else:
                                self.errors.append(f"Row {row_num}: {str(fk_error)}")
                            self.skipped_count += 1
                        
                    except Exception as e:
                        self.errors.append(f"Row {row_num}: {str(e)}")
                        self.skipped_count += 1
                        continue
            
            return True
        
        except Exception as e:
            self.errors.append(f"Error reading file: {str(e)}")
            return False
    
    def import_dividends(self, filepath):
        """
        Import dividends from CSV.
        Expected columns: Symbol, Amount Per Share, Quantity, Date
        """
        self.reset_counters()
        
        if not os.path.exists(filepath):
            self.errors.append(f"File not found: {filepath}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if not reader.fieldnames:
                    self.errors.append("CSV file is empty or invalid")
                    return False
                
                # Validate headers
                required_cols = {'Symbol', 'Amount Per Share', 'Quantity', 'Date'}
                csv_cols = set(col.strip() for col in reader.fieldnames)
                
                if not required_cols.issubset(csv_cols):
                    missing = required_cols - csv_cols
                    self.errors.append(f"Missing columns: {', '.join(missing)}")
                    return False
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        symbol = row['Symbol'].strip().upper()
                        amount_per_share_str = row['Amount Per Share'].strip()
                        quantity_str = row['Quantity'].strip()
                        date_str = row['Date'].strip()
                        
                        # Validate required fields
                        if not symbol:
                            self.errors.append(f"Row {row_num}: Symbol is empty")
                            self.skipped_count += 1
                            continue
                        
                        # Parse numeric fields
                        try:
                            amount_per_share = float(amount_per_share_str)
                            quantity = float(quantity_str)
                        except ValueError:
                            self.errors.append(f"Row {row_num}: Invalid number format")
                            self.skipped_count += 1
                            continue
                        
                        if amount_per_share < 0:
                            self.errors.append(f"Row {row_num}: Amount Per Share must be non-negative")
                            self.skipped_count += 1
                            continue
                        
                        if quantity <= 0:
                            self.errors.append(f"Row {row_num}: Quantity must be positive")
                            self.skipped_count += 1
                            continue
                        
                        # Validate date
                        parsed_date = self.validate_date(date_str)
                        if not parsed_date:
                            self.errors.append(f"Row {row_num}: Invalid date format '{date_str}'. Use YYYY-MM-DD")
                            self.skipped_count += 1
                            continue
                        
                        # Insert dividend
                        try:
                            db.add_dividend(symbol, amount_per_share, quantity, parsed_date)
                            self.imported_count += 1
                        except Exception as fk_error:
                            # Handle FOREIGN KEY constraint errors
                            if "FOREIGN KEY" in str(fk_error):
                                self.errors.append(f"Row {row_num}: Stock '{symbol}' not found. Try importing transactions first.")
                            else:
                                self.errors.append(f"Row {row_num}: {str(fk_error)}")
                            self.skipped_count += 1
                        
                    except Exception as e:
                        self.errors.append(f"Row {row_num}: {str(e)}")
                        self.skipped_count += 1
                        continue
            
            return True
        
        except Exception as e:
            self.errors.append(f"Error reading file: {str(e)}")
            return False
    
    def get_status_message(self):
        """Generate a status message summarizing the import results."""
        message = f"✓ Imported: {self.imported_count}\n"
        message += f"⊘ Skipped: {self.skipped_count}\n"
        
        if self.errors:
            message += f"\n⚠ Errors ({len(self.errors)}):\n"
            for error in self.errors[:10]:  # Show first 10 errors
                message += f"  • {error}\n"
            if len(self.errors) > 10:
                message += f"  • ... and {len(self.errors) - 10} more errors\n"
        
        return message.strip()
