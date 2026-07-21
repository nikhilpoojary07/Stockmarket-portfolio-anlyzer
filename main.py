"""
main.py — Stock Portfolio Analyzer
Main Tkinter Application Entry Point

Tech Stack: Python 3.x | Tkinter + ttk | SQLite3 | Matplotlib | yfinance | scikit-learn
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import datetime
import threading

# ── Matplotlib embedded in Tkinter ──────────────────────────────────────────
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ── Internal modules ─────────────────────────────────────────────────────────
import database as db
import price_fetcher
import predictor
import exporter
import importer

# ── Theme colours ─────────────────────────────────────────────────────────────
DARK = {
    "bg":     "#1e1e2e",
    "panel":  "#2a2a3e",
    "accent": "#7c3aed",
    "green":  "#22c55e",
    "red":    "#ef4444",
    "text":   "#e2e8f0",
    "sub":    "#94a3b8",
    "header": "#0f172a",
    "border": "#334155",
}

LIGHT = {
    "bg":     "#f8fafc",
    "panel":  "#ffffff",
    "accent": "#6d28d9",
    "green":  "#16a34a",
    "red":    "#dc2626",
    "text":   "#0f172a",
    "sub":    "#475569",
    "header": "#e2e8f0",
    "border": "#cbd5e1",
}

THEME = DARK          # Default theme; toggled at runtime
FONT  = ("Segoe UI", 10)
FONT_B = ("Segoe UI", 10, "bold")
FONT_H = ("Segoe UI", 14, "bold")
FONT_S = ("Segoe UI Semibold", 11)


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility helpers
# ═══════════════════════════════════════════════════════════════════════════════

def fmt_inr(val: float) -> str:
    """Format a float as ₹ with commas."""
    try:
        return f"₹{val:,.2f}"
    except Exception:
        return "₹0.00"


def color_pnl(val: float) -> str:
    return THEME["green"] if val >= 0 else THEME["red"]


def today() -> str:
    return datetime.date.today().isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
#  Styled widgets
# ═══════════════════════════════════════════════════════════════════════════════

def make_label(parent, text, font=FONT, fg=None, bg=None, **kw):
    fg = fg or THEME["text"]
    bg = bg or THEME["bg"]
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)


def make_entry(parent, width=18, **kw):
    e = tk.Entry(parent, width=width, font=FONT,
                 bg=THEME["panel"], fg=THEME["text"],
                 insertbackground=THEME["text"],
                 relief="flat", bd=4, **kw)
    return e


def make_button(parent, text, command, bg=None, fg=None, **kw):
    bg = bg or THEME["accent"]
    fg = fg or "#ffffff"
    b = tk.Button(parent, text=text, command=command,
                  bg=bg, fg=fg, font=FONT_B,
                  activebackground=THEME["sub"],
                  relief="flat", padx=10, pady=5, cursor="hand2", **kw)
    return b


def make_tree(parent, columns, heights=15):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Custom.Treeview",
                    background=THEME["panel"],
                    foreground=THEME["text"],
                    fieldbackground=THEME["panel"],
                    rowheight=28,
                    font=FONT)
    style.configure("Custom.Treeview.Heading",
                    background=THEME["header"],
                    foreground=THEME["text"],
                    font=FONT_B)
    style.map("Custom.Treeview",
              background=[("selected", THEME["accent"])],
              foreground=[("selected", "#ffffff")])

    tree = ttk.Treeview(parent, columns=columns, show="headings",
                        height=heights, style="Custom.Treeview")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=110)
    sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    return tree, sb


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Application
# ═══════════════════════════════════════════════════════════════════════════════

class StockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        db.init_db()

        self.title("📈 Stock Portfolio Analyzer")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        self.configure(bg=THEME["bg"])

        self._price_cache: dict = db.get_price_cache()
        self._holdings:    dict = {}
        self._refresh_lock = threading.Lock()

        self._build_ui()
        self.after(500, self._refresh_holdings_tab)

    # ── UI skeleton ──────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg=THEME["header"], height=56)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="📈  Stock Portfolio Analyzer",
                 font=("Segoe UI", 16, "bold"),
                 fg=THEME["accent"], bg=THEME["header"]).pack(side="left", padx=20)

        make_button(top, "🔄 Refresh Prices", self._fetch_prices_thread,
                    bg=THEME["green"]).pack(side="right", padx=10, pady=8)
        make_button(top, "🌗 Toggle Theme", self._toggle_theme).pack(side="right", padx=4, pady=8)

        # Summary strip
        self._sum_frame = tk.Frame(self, bg=THEME["panel"], height=48)
        self._sum_frame.pack(fill="x", pady=(2, 0))
        self._sum_frame.pack_propagate(False)
        self._sum_labels = {}
        for key in ["Invested", "Market Value", "P&L", "P&L %", "Day Gain"]:
            f = tk.Frame(self._sum_frame, bg=THEME["panel"])
            f.pack(side="left", padx=22)
            tk.Label(f, text=key, font=("Segoe UI", 8),
                     fg=THEME["sub"], bg=THEME["panel"]).pack()
            lbl = tk.Label(f, text="—", font=FONT_S,
                           fg=THEME["text"], bg=THEME["panel"])
            lbl.pack()
            self._sum_labels[key] = lbl

        # Notebook (tabs)
        style = ttk.Style()
        style.configure("TNotebook", background=THEME["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=THEME["panel"],
                        foreground=THEME["text"], font=FONT_B,
                        padding=[14, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", THEME["accent"])],
                  foreground=[("selected", "#ffffff")])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=4)

        self._tabs = {}
        tab_defs = [
            ("Holdings",     self._build_holdings_tab),
            ("Transactions", self._build_transactions_tab),
            ("Watchlist",    self._build_watchlist_tab),
            ("Dividends",    self._build_dividends_tab),
            ("Analytics",    self._build_analytics_tab),
            ("📊 Prediction", self._build_prediction_tab),
        ]
        for name, builder in tab_defs:
            frame = tk.Frame(nb, bg=THEME["bg"])
            nb.add(frame, text=f"  {name}  ")
            self._tabs[name] = frame
            builder(frame)

    # ── Summary strip update ─────────────────────────────────────────────────

    def _update_summary(self):
        h = self._holdings
        cache = self._price_cache

        invested = sum(d["invested"] for d in h.values())
        market   = sum(h[s]["qty"] * cache.get(s, {}).get("ltp", 0) for s in h)
        pnl      = market - invested
        pnl_pct  = (pnl / invested * 100) if invested else 0
        day_gain = sum(
            h[s]["qty"] * (cache.get(s, {}).get("ltp", 0) - cache.get(s, {}).get("prev_close", 0))
            for s in h
        )

        self._sum_labels["Invested"].config(text=fmt_inr(invested))
        self._sum_labels["Market Value"].config(text=fmt_inr(market))
        self._sum_labels["P&L"].config(text=fmt_inr(pnl), fg=color_pnl(pnl))
        self._sum_labels["P&L %"].config(text=f"{pnl_pct:+.2f}%", fg=color_pnl(pnl))
        self._sum_labels["Day Gain"].config(text=fmt_inr(day_gain), fg=color_pnl(day_gain))

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 1 — Holdings
    # ════════════════════════════════════════════════════════════════════════

    def _build_holdings_tab(self, parent):
        cols = ("Symbol", "Qty", "Avg Cost", "LTP", "Invested", "Mkt Value", "P&L", "P&L %", "Day Gain")
        tree, sb = make_tree(parent, cols, heights=22)
        tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="left", fill="y", pady=8)

        # Tag colours
        tree.tag_configure("profit", foreground=THEME["green"])
        tree.tag_configure("loss",   foreground=THEME["red"])

        self._holdings_tree = tree

        btn_f = tk.Frame(parent, bg=THEME["bg"])
        btn_f.pack(side="right", fill="y", padx=10, pady=8)
        make_button(btn_f, "📥 Export CSV", self._export_holdings).pack(pady=6)

    def _refresh_holdings_tab(self):
        self._holdings = db.get_holdings()
        cache = self._price_cache
        tree = self._holdings_tree
        tree.delete(*tree.get_children())

        for sym, h in sorted(self._holdings.items()):
            ltp        = cache.get(sym, {}).get("ltp", 0)
            prev_close = cache.get(sym, {}).get("prev_close", 0)
            cur_val    = h["qty"] * ltp
            pnl        = cur_val - h["invested"]
            pnl_pct    = (pnl / h["invested"] * 100) if h["invested"] else 0
            day_gain   = h["qty"] * (ltp - prev_close)
            tag        = "profit" if pnl >= 0 else "loss"

            tree.insert("", "end", values=(
                sym,
                f"{h['qty']:.2f}",
                fmt_inr(h["avg_cost"]),
                fmt_inr(ltp),
                fmt_inr(h["invested"]),
                fmt_inr(cur_val),
                fmt_inr(pnl),
                f"{pnl_pct:+.2f}%",
                fmt_inr(day_gain),
            ), tags=(tag,))

        self._update_summary()

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 2 — Transactions
    # ════════════════════════════════════════════════════════════════════════

    def _build_transactions_tab(self, parent):
        # Form
        form = tk.LabelFrame(parent, text="  Add Transaction  ",
                             bg=THEME["bg"], fg=THEME["sub"], font=FONT_B,
                             bd=1, relief="groove")
        form.pack(fill="x", padx=10, pady=(10, 4))

        fields = [("Symbol", 12), ("Type (BUY/SELL)", 10), ("Qty", 10),
                  ("Price ₹", 10), ("Brokerage ₹", 10), ("Date (YYYY-MM-DD)", 14)]
        self._txn_entries = {}
        for i, (label, w) in enumerate(fields):
            tk.Label(form, text=label, font=FONT, bg=THEME["bg"], fg=THEME["sub"]).grid(
                row=0, column=i * 2, padx=(12, 4), pady=8)
            e = make_entry(form, width=w)
            e.grid(row=0, column=i * 2 + 1, padx=(0, 8))
            self._txn_entries[label] = e

        self._txn_entries["Date (YYYY-MM-DD)"].insert(0, today())

        bf = tk.Frame(form, bg=THEME["bg"])
        bf.grid(row=0, column=len(fields) * 2, padx=8)
        make_button(bf, "➕ Add", self._add_transaction, bg=THEME["green"]).pack(side="left", padx=4)
        make_button(bf, "🗑 Delete", self._delete_transaction, bg=THEME["red"]).pack(side="left")
        make_button(bf, "📥 Import CSV", self._import_transactions_csv, bg=THEME["accent"]).pack(side="left", padx=4)

        # Table
        cols = ("ID", "Symbol", "Type", "Qty", "Price", "Brokerage", "Date")
        tree, sb = make_tree(parent, cols, heights=18)
        tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        tree.tag_configure("buy",  foreground=THEME["green"])
        tree.tag_configure("sell", foreground=THEME["red"])
        self._txn_tree = tree
        self._refresh_txn_table()

        make_button(parent, "📥 Export CSV", self._export_transactions).pack(pady=8)

    def _refresh_txn_table(self, symbol=None):
        tree = self._txn_tree
        tree.delete(*tree.get_children())
        for row in db.get_transactions(symbol):
            tag = "buy" if row[2] == "BUY" else "sell"
            tree.insert("", "end", values=row, tags=(tag,))

    def _validate_stock_price(self, sym: str, entered_price: float) -> float:
        """
        Validate entered price against live trading price.
        Returns the price to use (entered or live).
        Shows warning if price differs by >15% from live price.
        """
        try:
            # Fetch live price for the symbol
            live_prices = price_fetcher.fetch_prices([sym])
            if sym not in live_prices or not live_prices[sym]:
                return entered_price  # No live price available, use entered
            
            live_price = live_prices[sym].get("ltp", 0)
            if live_price <= 0:
                return entered_price  # Invalid live price, use entered
            
            # Calculate percentage difference
            pct_diff = abs((entered_price - live_price) / live_price) * 100
            
            # If difference > 15%, show warning
            if pct_diff > 15:
                response = messagebox.showerror(
                    "⚠️  Price Alert",
                    f"The price you entered (₹{entered_price:.2f}) differs significantly "
                    f"from the live trading price (₹{live_price:.2f}).\n\n"
                    f"Difference: {pct_diff:.1f}%\n\n"
                    f"Click 'Retry' to cancel and use the live price,\n"
                    f"or 'Ignore' to proceed with your entered price.",
                    type=messagebox.RETRYCANCEL
                )
                
                # RETRY (button 4) = use live price, CANCEL (button 1) = use entered price
                if response == "retry":  # User clicked Retry
                    messagebox.showinfo(
                        "Price Updated",
                        f"Using live trading price: ₹{live_price:.2f}"
                    )
                    return live_price
                else:  # User clicked Cancel / Ignore
                    return entered_price
            
            return entered_price
            
        except Exception as e:
            print(f"Price validation error: {e}")
            return entered_price  # On error, use entered price
    
    def _add_transaction(self):
        e = self._txn_entries
        sym  = e["Symbol"].get().strip().upper()
        typ  = e["Type (BUY/SELL)"].get().strip().upper()
        qty  = e["Qty"].get().strip()
        price = e["Price ₹"].get().strip()
        brok  = e["Brokerage ₹"].get().strip() or "0"
        date  = e["Date (YYYY-MM-DD)"].get().strip()

        if not all([sym, typ, qty, price, date]):
            messagebox.showerror("Error", "All fields except Brokerage are required.")
            return
        if typ not in ("BUY", "SELL"):
            messagebox.showerror("Error", "Type must be BUY or SELL.")
            return
        try:
            qty_f   = float(qty)
            price_f = float(price)
            brok_f  = float(brok)
        except ValueError:
            messagebox.showerror("Error", "Qty / Price / Brokerage must be numbers.")
            return

        # Auto-add stock if not present
        stocks = {s[0] for s in db.get_all_stocks()}
        if sym not in stocks:
            db.add_stock(sym, sym, "Unknown", "NSE")

        # Validate price against live trading price
        validated_price = self._validate_stock_price(sym, price_f)
        
        db.add_transaction(sym, typ, qty_f, validated_price, brok_f, date)
        self._refresh_txn_table()
        self._refresh_holdings_tab()
        messagebox.showinfo("Success", f"{typ} {qty_f} × {sym} recorded.")

    def _delete_transaction(self):
        sel = self._txn_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a transaction to delete.")
            return
        txn_id = self._txn_tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Confirm", f"Delete transaction #{txn_id}?"):
            db.delete_transaction(txn_id)
            self._refresh_txn_table()
            self._refresh_holdings_tab()

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 3 — Watchlist
    # ════════════════════════════════════════════════════════════════════════

    def _build_watchlist_tab(self, parent):
        form = tk.LabelFrame(parent, text="  Add to Watchlist  ",
                             bg=THEME["bg"], fg=THEME["sub"], font=FONT_B,
                             bd=1, relief="groove")
        form.pack(fill="x", padx=10, pady=(10, 4))

        self._wl_entries = {}
        for i, (lbl, w) in enumerate([("Symbol", 10), ("Company", 20), ("Target ₹", 10)]):
            tk.Label(form, text=lbl, font=FONT, bg=THEME["bg"], fg=THEME["sub"]).grid(
                row=0, column=i * 2, padx=12, pady=8)
            e = make_entry(form, width=w)
            e.grid(row=0, column=i * 2 + 1)
            self._wl_entries[lbl] = e

        bf = tk.Frame(form, bg=THEME["bg"])
        bf.grid(row=0, column=6, padx=10)
        make_button(bf, "➕ Add", self._add_watchlist, bg=THEME["green"]).pack(side="left", padx=4)
        make_button(bf, "🗑 Remove", self._del_watchlist, bg=THEME["red"]).pack(side="left")
        make_button(bf, "📥 Import CSV", self._import_watchlist_csv, bg=THEME["accent"]).pack(side="left", padx=4)

        cols = ("ID", "Symbol", "Company", "Target ₹", "LTP", "Gap %", "Added")
        tree, sb = make_tree(parent, cols, heights=18)
        tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        tree.tag_configure("near",   foreground=THEME["green"])
        tree.tag_configure("far",    foreground=THEME["red"])
        self._wl_tree = tree
        self._refresh_wl_table()

    def _refresh_wl_table(self):
        tree = self._wl_tree
        tree.delete(*tree.get_children())
        cache = self._price_cache
        for row in db.get_watchlist():
            wid, sym, comp, target, added = row
            ltp = cache.get(sym, {}).get("ltp", 0)
            gap = ((target - ltp) / ltp * 100) if ltp else 0
            tag = "near" if abs(gap) <= 5 else "far"
            tree.insert("", "end", values=(
                wid, sym, comp or "—",
                fmt_inr(target), fmt_inr(ltp), f"{gap:+.2f}%", added or "—"
            ), tags=(tag,))

    def _add_watchlist(self):
        sym    = self._wl_entries["Symbol"].get().strip().upper()
        comp   = self._wl_entries["Company"].get().strip()
        target = self._wl_entries["Target ₹"].get().strip()
        if not sym or not target:
            messagebox.showerror("Error", "Symbol and Target Price are required.")
            return
        try:
            target_f = float(target)
        except ValueError:
            messagebox.showerror("Error", "Target must be a number.")
            return
        db.add_watchlist(sym, comp, target_f, today())
        self._refresh_wl_table()

    def _del_watchlist(self):
        sel = self._wl_tree.selection()
        if not sel:
            return
        wid = self._wl_tree.item(sel[0])["values"][0]
        db.delete_watchlist(wid)
        self._refresh_wl_table()

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 4 — Dividends
    # ════════════════════════════════════════════════════════════════════════

    def _build_dividends_tab(self, parent):
        form = tk.LabelFrame(parent, text="  Log Dividend  ",
                             bg=THEME["bg"], fg=THEME["sub"], font=FONT_B,
                             bd=1, relief="groove")
        form.pack(fill="x", padx=10, pady=(10, 4))

        self._div_entries = {}
        for i, (lbl, w) in enumerate([("Symbol", 10), ("₹ / Share", 10),
                                       ("Qty", 10), ("Date", 12)]):
            tk.Label(form, text=lbl, font=FONT, bg=THEME["bg"], fg=THEME["sub"]).grid(
                row=0, column=i * 2, padx=12, pady=8)
            e = make_entry(form, width=w)
            e.grid(row=0, column=i * 2 + 1)
            self._div_entries[lbl] = e
        self._div_entries["Date"].insert(0, today())

        bf = tk.Frame(form, bg=THEME["bg"])
        bf.grid(row=0, column=8, padx=10)
        make_button(bf, "➕ Add", self._add_dividend, bg=THEME["green"]).pack(side="left", padx=4)
        make_button(bf, "🗑 Delete", self._del_dividend, bg=THEME["red"]).pack(side="left")
        make_button(bf, "📥 Import CSV", self._import_dividends_csv, bg=THEME["accent"]).pack(side="left", padx=4)

        cols = ("ID", "Symbol", "₹/Share", "Qty", "Total", "Date")
        tree, sb = make_tree(parent, cols, heights=16)
        tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self._div_tree = tree
        self._refresh_div_table()

        # Total income label
        self._div_total_lbl = tk.Label(parent, text="Total Dividend Income: ₹0.00",
                                        font=FONT_B, bg=THEME["bg"], fg=THEME["green"])
        self._div_total_lbl.pack(pady=4)

    def _refresh_div_table(self):
        tree = self._div_tree
        tree.delete(*tree.get_children())
        total = 0
        for row in db.get_dividends():
            did, sym, aps, qty, date = row
            total_div = aps * qty
            total += total_div
            tree.insert("", "end", values=(did, sym, fmt_inr(aps), qty, fmt_inr(total_div), date))
        if hasattr(self, "_div_total_lbl"):
            self._div_total_lbl.config(text=f"Total Dividend Income: {fmt_inr(total)}")

    def _add_dividend(self):
        e = self._div_entries
        sym  = e["Symbol"].get().strip().upper()
        aps  = e["₹ / Share"].get().strip()
        qty  = e["Qty"].get().strip()
        date = e["Date"].get().strip()
        if not all([sym, aps, qty, date]):
            messagebox.showerror("Error", "All fields required.")
            return
        try:
            db.add_dividend(sym, float(aps), float(qty), date)
        except ValueError:
            messagebox.showerror("Error", "Amount and Qty must be numbers.")
            return
        self._refresh_div_table()

    def _del_dividend(self):
        sel = self._div_tree.selection()
        if not sel:
            return
        did = self._div_tree.item(sel[0])["values"][0]
        db.delete_dividend(did)
        self._refresh_div_table()

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 5 — Analytics
    # ════════════════════════════════════════════════════════════════════════

    def _build_analytics_tab(self, parent):
        btn_row = tk.Frame(parent, bg=THEME["bg"])
        btn_row.pack(fill="x", padx=10, pady=6)

        make_button(btn_row, "🥧 Allocation Pie",    self._chart_pie).pack(side="left", padx=6)
        make_button(btn_row, "📊 P&L Bar",           self._chart_pnl_bar).pack(side="left", padx=6)
        make_button(btn_row, "📈 NAV Trend",          self._chart_nav).pack(side="left", padx=6)
        make_button(btn_row, "🏭 Sector Breakdown",   self._chart_sector).pack(side="left", padx=6)

        self._analytics_canvas_frame = tk.Frame(parent, bg=THEME["bg"])
        self._analytics_canvas_frame.pack(fill="both", expand=True, padx=10, pady=4)
        self._chart_pie()   # show default chart

    def _clear_chart(self):
        for w in self._analytics_canvas_frame.winfo_children():
            w.destroy()

    def _embed_fig(self, fig):
        self._clear_chart()
        canvas = FigureCanvasTkAgg(fig, master=self._analytics_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    def _chart_pie(self):
        h = self._holdings
        cache = self._price_cache
        if not h:
            messagebox.showinfo("No Data", "No holdings found.")
            return
        labels, sizes = [], []
        for sym, d in h.items():
            val = d["qty"] * cache.get(sym, {}).get("ltp", d["avg_cost"])
            if val > 0:
                labels.append(sym)
                sizes.append(val)
        if not sizes:
            return
        fig = Figure(figsize=(9, 5), facecolor=THEME["bg"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(THEME["bg"])
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct="%1.1f%%",
            startangle=140,
            textprops={"color": THEME["text"], "fontsize": 9}
        )
        ax.set_title("Portfolio Allocation by Market Value",
                     color=THEME["text"], fontsize=13, pad=14)
        self._embed_fig(fig)

    def _chart_pnl_bar(self):
        h = self._holdings
        cache = self._price_cache
        if not h:
            return
        syms, pnls = [], []
        for sym, d in sorted(h.items()):
            ltp  = cache.get(sym, {}).get("ltp", 0)
            pnl  = d["qty"] * ltp - d["invested"]
            syms.append(sym)
            pnls.append(pnl)
        colors = [THEME["green"] if p >= 0 else THEME["red"] for p in pnls]
        fig = Figure(figsize=(9, 5), facecolor=THEME["bg"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(THEME["bg"])
        bars = ax.bar(syms, pnls, color=colors)
        ax.axhline(0, color=THEME["sub"], linewidth=0.8)
        ax.set_title("Unrealised P&L per Stock", color=THEME["text"], fontsize=13)
        ax.tick_params(colors=THEME["text"])
        ax.set_ylabel("P&L (₹)", color=THEME["text"])
        for spine in ax.spines.values():
            spine.set_edgecolor(THEME["border"])
        self._embed_fig(fig)

    def _chart_nav(self):
        txns = db.get_transactions()
        if not txns:
            messagebox.showinfo("No Data", "No transactions found.")
            return
        # Build cumulative invested value by date
        from collections import defaultdict
        daily = defaultdict(float)
        for _, sym, typ, qty, price, brok, date in txns:
            cost = qty * price + brok
            daily[date] += cost if typ == "BUY" else -cost
        dates_sorted = sorted(daily)
        cum, running = [], 0.0
        for d in dates_sorted:
            running += daily[d]
            cum.append(running)
        import matplotlib.dates as mdates
        fig = Figure(figsize=(9, 5), facecolor=THEME["bg"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(THEME["bg"])
        ax.plot([datetime.date.fromisoformat(d) for d in dates_sorted],
                cum, color=THEME["accent"], linewidth=2, marker="o", markersize=4)
        ax.fill_between([datetime.date.fromisoformat(d) for d in dates_sorted],
                        cum, alpha=0.15, color=THEME["accent"])
        ax.set_title("Portfolio NAV Trend (Cumulative Invested)", color=THEME["text"], fontsize=13)
        ax.tick_params(colors=THEME["text"])
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
        for spine in ax.spines.values():
            spine.set_edgecolor(THEME["border"])
        self._embed_fig(fig)

    def _chart_sector(self):
        stocks = {s[0]: s[2] for s in db.get_all_stocks()}
        h = self._holdings
        cache = self._price_cache
        if not h:
            return
        from collections import defaultdict
        sec_val = defaultdict(float)
        for sym, d in h.items():
            sector = stocks.get(sym, "Unknown")
            val = d["qty"] * cache.get(sym, {}).get("ltp", d["avg_cost"])
            sec_val[sector] += val
        labels = list(sec_val.keys())
        sizes  = list(sec_val.values())
        fig = Figure(figsize=(9, 5), facecolor=THEME["bg"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(THEME["bg"])
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90,
               textprops={"color": THEME["text"], "fontsize": 9})
        ax.set_title("Sector-wise Allocation", color=THEME["text"], fontsize=13)
        self._embed_fig(fig)

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 6 — 📊 Prediction
    # ════════════════════════════════════════════════════════════════════════

    def _build_prediction_tab(self, parent):
        # Header
        tk.Label(parent,
                 text="🤖  ML Stock Price Prediction  (Linear Regression + Technical Indicators)",
                 font=FONT_H, bg=THEME["bg"], fg=THEME["accent"]).pack(pady=(14, 4))
        tk.Label(parent,
                 text="Features: MA7 · MA21 · MA50 · RSI · Momentum · Volatility",
                 font=("Segoe UI", 9), bg=THEME["bg"], fg=THEME["sub"]).pack()

        # Controls row
        ctrl = tk.Frame(parent, bg=THEME["bg"])
        ctrl.pack(pady=10)
        tk.Label(ctrl, text="Symbol:", font=FONT, bg=THEME["bg"], fg=THEME["sub"]).pack(side="left")
        self._pred_sym = make_entry(ctrl, width=12)
        self._pred_sym.pack(side="left", padx=6)

        tk.Label(ctrl, text="Days Ahead:", font=FONT, bg=THEME["bg"], fg=THEME["sub"]).pack(side="left")
        self._pred_days = make_entry(ctrl, width=6)
        self._pred_days.insert(0, "7")
        self._pred_days.pack(side="left", padx=6)

        make_button(ctrl, "🔮 Predict", self._run_prediction,
                    bg=THEME["accent"]).pack(side="left", padx=10)

        # Result info panel
        self._pred_info = tk.Frame(parent, bg=THEME["panel"], bd=1, relief="groove")
        self._pred_info.pack(fill="x", padx=30, pady=4)
        self._pred_info_labels = {}
        info_keys = ["Current Price", "Predicted Price", "Direction",
                     "Change %", "Confidence", "Back-test MAPE",
                     "MA7", "MA21", "RSI"]
        for i, k in enumerate(info_keys):
            col = i % 3
            row = i // 3
            f = tk.Frame(self._pred_info, bg=THEME["panel"])
            f.grid(row=row, column=col, padx=20, pady=8, sticky="w")
            tk.Label(f, text=k, font=("Segoe UI", 8),
                     bg=THEME["panel"], fg=THEME["sub"]).pack(anchor="w")
            lbl = tk.Label(f, text="—", font=FONT_B,
                           bg=THEME["panel"], fg=THEME["text"])
            lbl.pack(anchor="w")
            self._pred_info_labels[k] = lbl

        # Chart area
        self._pred_chart_frame = tk.Frame(parent, bg=THEME["bg"])
        self._pred_chart_frame.pack(fill="both", expand=True, padx=10, pady=4)

        # Status
        self._pred_status = tk.Label(parent, text="Enter a symbol and click Predict.",
                                      font=FONT, bg=THEME["bg"], fg=THEME["sub"])
        self._pred_status.pack(pady=4)

    def _run_prediction(self):
        sym  = self._pred_sym.get().strip().upper()
        days = self._pred_days.get().strip()
        if not sym:
            messagebox.showerror("Error", "Enter a stock symbol.")
            return
        try:
            days_int = int(days)
            if days_int < 1 or days_int > 90:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Days ahead must be 1–90.")
            return

        self._pred_status.config(text=f"⏳ Fetching data and training model for {sym}...")
        self.update_idletasks()

        def worker():
            result = predictor.predict(sym, days_ahead=days_int)
            self.after(0, lambda: self._show_prediction(result))

        threading.Thread(target=worker, daemon=True).start()

    def _show_prediction(self, r: dict):
        if r.get("error"):
            self._pred_status.config(text=f"❌ Error: {r['error']}")
            return

        sym  = r["symbol"]
        info = self._pred_info_labels
        dir_color = THEME["green"] if r["direction"] == "UP" else (
                    THEME["red"] if r["direction"] == "DOWN" else THEME["sub"])

        info["Current Price"].config(  text=fmt_inr(r["current_price"]))
        info["Predicted Price"].config(text=fmt_inr(r["predicted_price"]))
        info["Direction"].config(      text=r["direction"], fg=dir_color)
        info["Change %"].config(       text=f"{r.get('change_pct', 0):+.2f}%", fg=dir_color)
        info["Confidence"].config(     text=f"{r['confidence']}%")
        info["Back-test MAPE"].config( text=f"{r['mape']:.2f}%")
        info["MA7"].config(            text=fmt_inr(r["ma7"]))
        info["MA21"].config(           text=fmt_inr(r["ma21"]))
        info["RSI"].config(            text=f"{r['rsi']:.1f}")

        # Chart
        for w in self._pred_chart_frame.winfo_children():
            w.destroy()

        series = r["forecast_series"]
        dates  = [datetime.date.fromisoformat(d) for d, _ in series]
        prices = [p for _, p in series]

        fig = Figure(figsize=(9, 4), facecolor=THEME["bg"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(THEME["bg"])

        # Historical last 30 days from cache (or just show forecast)
        hist_df = price_fetcher.fetch_history(sym, period="3mo")
        if hist_df is not None and not hist_df.empty:
            hist_close = hist_df["Close"].squeeze()
            hist_dates = [d.date() if hasattr(d, "date") else d for d in hist_df.index]
            ax.plot(hist_dates, hist_close,
                    color=THEME["sub"], linewidth=1.5, label="Historical")

        ax.plot(dates, prices, color=THEME["accent"],
                linewidth=2, marker="o", markersize=5,
                linestyle="--", label=f"Forecast ({len(series)}d)")
        ax.fill_between(dates, prices, alpha=0.12, color=THEME["accent"])
        ax.axhline(r["current_price"], color=THEME["text"],
                   linewidth=0.8, linestyle=":", alpha=0.5)

        ax.set_title(f"{sym} — {len(series)}-Day Price Forecast",
                     color=THEME["text"], fontsize=12)
        ax.tick_params(colors=THEME["text"])
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.legend(facecolor=THEME["panel"], labelcolor=THEME["text"])
        for spine in ax.spines.values():
            spine.set_edgecolor(THEME["border"])

        canvas = FigureCanvasTkAgg(fig, master=self._pred_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

        self._pred_status.config(
            text=f"✅ Prediction complete for {sym} · "
                 f"Target date: {r['predicted_date']} · "
                 f"Confidence: {r['confidence']}%"
        )

    # ════════════════════════════════════════════════════════════════════════
    #  Price Refresh (background thread)
    # ════════════════════════════════════════════════════════════════════════

    def _fetch_prices_thread(self):
        symbols = list(self._holdings.keys())
        if not symbols:
            messagebox.showinfo("Info", "No holdings to fetch prices for.")
            return
        self._sum_labels["Invested"].config(text="⏳ Fetching...")
        self.update_idletasks()

        def worker():
            result = price_fetcher.fetch_prices(symbols)
            self._price_cache.update(result)
            self.after(0, self._refresh_holdings_tab)
            self.after(0, self._refresh_wl_table)

        threading.Thread(target=worker, daemon=True).start()

    # ════════════════════════════════════════════════════════════════════════
    #  Theme toggle
    # ════════════════════════════════════════════════════════════════════════

    def _toggle_theme(self):
        global THEME
        THEME = LIGHT if THEME == DARK else DARK
        messagebox.showinfo("Theme", "Restart the application to apply the new theme fully.")

    # ════════════════════════════════════════════════════════════════════════
    #  Admin panel
    # ════════════════════════════════════════════════════════════════════════

    def _admin_login(self):
        win = tk.Toplevel(self)
        win.title("Admin Login")
        win.configure(bg=THEME["bg"])
        win.geometry("340x200")
        win.resizable(False, False)

        tk.Label(win, text="Admin Login", font=FONT_H,
                 bg=THEME["bg"], fg=THEME["accent"]).pack(pady=14)

        form = tk.Frame(win, bg=THEME["bg"])
        form.pack()
        tk.Label(form, text="Username:", font=FONT, bg=THEME["bg"], fg=THEME["sub"]).grid(row=0, column=0, padx=10, pady=6)
        usr = make_entry(form, width=18)
        usr.grid(row=0, column=1)
        usr.insert(0, "admin")

        tk.Label(form, text="Password:", font=FONT, bg=THEME["bg"], fg=THEME["sub"]).grid(row=1, column=0, padx=10, pady=6)
        pwd = make_entry(form, width=18, show="*")
        pwd.grid(row=1, column=1)

        def login():
            if db.verify_admin(usr.get(), pwd.get()):
                win.destroy()
                self._admin_dashboard()
            else:
                messagebox.showerror("Error", "Invalid credentials.", parent=win)

        make_button(win, "Login", login, bg=THEME["accent"]).pack(pady=12)

    def _admin_dashboard(self):
        win = tk.Toplevel(self)
        win.title("Admin Dashboard")
        win.configure(bg=THEME["bg"])
        win.geometry("700x550")

        tk.Label(win, text="🔐 Admin Dashboard", font=FONT_H,
                 bg=THEME["bg"], fg=THEME["accent"]).pack(pady=12)

        btn_f = tk.Frame(win, bg=THEME["bg"])
        btn_f.pack(pady=8)

        make_button(btn_f, "📋 View All Stocks",   lambda: self._admin_stocks(win)).pack(side="left", padx=8)
        make_button(btn_f, "➕ Add Stock",          lambda: self._admin_add_stock(win)).pack(side="left", padx=8)
        make_button(btn_f, "📥 Backup DB to CSV",  self._export_full_backup).pack(side="left", padx=8)

        # Stock list
        f = tk.Frame(win, bg=THEME["bg"])
        f.pack(fill="both", expand=True, padx=12, pady=8)
        cols = ("Symbol", "Company", "Sector", "Exchange")
        tree, sb = make_tree(f, cols, heights=16)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

        def refresh():
            tree.delete(*tree.get_children())
            for row in db.get_all_stocks():
                tree.insert("", "end", values=row)

        refresh()
        win._stock_tree = tree
        win._refresh    = refresh

        make_button(win, "🗑 Delete Selected Stock",
                    lambda: self._admin_del_stock(win._stock_tree, win._refresh),
                    bg=THEME["red"]).pack(pady=6)

    def _admin_stocks(self, parent):
        parent._refresh()

    def _admin_add_stock(self, parent):
        win = tk.Toplevel(parent)
        win.title("Add Stock")
        win.configure(bg=THEME["bg"])
        win.geometry("380x240")

        entries = {}
        for i, (lbl, default) in enumerate([("Symbol", ""), ("Company", ""), ("Sector", "Unknown"), ("Exchange", "NSE")]):
            tk.Label(win, text=lbl, font=FONT, bg=THEME["bg"], fg=THEME["sub"]).grid(row=i, column=0, padx=14, pady=8)
            e = make_entry(win, width=22)
            e.insert(0, default)
            e.grid(row=i, column=1)
            entries[lbl] = e

        def save():
            sym  = entries["Symbol"].get().strip().upper()
            comp = entries["Company"].get().strip()
            sec  = entries["Sector"].get().strip()
            exc  = entries["Exchange"].get().strip()
            if not sym or not comp:
                messagebox.showerror("Error", "Symbol and Company required.", parent=win)
                return
            db.add_stock(sym, comp, sec, exc)
            win.destroy()
            parent._refresh()

        make_button(win, "Save", save, bg=THEME["green"]).grid(row=4, column=1, pady=12)

    def _admin_del_stock(self, tree, refresh):
        sel = tree.selection()
        if not sel:
            return
        sym = tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Confirm", f"Delete {sym} and all related data?"):
            db.delete_stock(sym)
            refresh()

    def _import_transactions_csv(self):
        """Import transactions from a CSV file."""
        filepath = filedialog.askopenfilename(
            title="Select Transactions CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filepath:
            return
        
        # Run import in background thread
        def do_import():
            csv_importer = importer.CSVImporter()
            success = csv_importer.import_transactions(filepath)
            
            # Update UI on main thread
            self.after(0, lambda: self._show_import_result(csv_importer, "Transactions"))
        
        thread = threading.Thread(target=do_import, daemon=True)
        thread.start()
    
    def _import_watchlist_csv(self):
        """Import watchlist from a CSV file."""
        filepath = filedialog.askopenfilename(
            title="Select Watchlist CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filepath:
            return
        
        def do_import():
            csv_importer = importer.CSVImporter()
            success = csv_importer.import_watchlist(filepath)
            
            self.after(0, lambda: self._show_import_result(csv_importer, "Watchlist"))
        
        thread = threading.Thread(target=do_import, daemon=True)
        thread.start()
    
    def _import_dividends_csv(self):
        """Import dividends from a CSV file."""
        filepath = filedialog.askopenfilename(
            title="Select Dividends CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filepath:
            return
        
        def do_import():
            csv_importer = importer.CSVImporter()
            success = csv_importer.import_dividends(filepath)
            
            self.after(0, lambda: self._show_import_result(csv_importer, "Dividends"))
        
        thread = threading.Thread(target=do_import, daemon=True)
        thread.start()
    
    def _show_import_result(self, csv_importer, data_type):
        """Display import result dialog and refresh UI."""
        status_msg = csv_importer.get_status_message()
        
        # Show result dialog
        messagebox.showinfo(f"{data_type} Import Complete", status_msg)
        
        # Refresh all relevant tabs
        self._refresh_txn_table()
        self._refresh_wl_table()
        self._refresh_div_table()
        self._refresh_holdings_tab()

    # ────────────────────────────────────────────────────────────────────────────

    def _export_full_backup(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            exporter.export_transactions(path)
            messagebox.showinfo("Done", f"Exported to {path}")

    # ── Export helpers ───────────────────────────────────────────────────────

    def _export_holdings(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            exporter.export_holdings(path)
            messagebox.showinfo("Exported", f"Holdings saved to:\n{path}")

    def _export_transactions(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            exporter.export_transactions(path)
            messagebox.showinfo("Exported", f"Transactions saved to:\n{path}")


# ═══════════════════════════════════════════════════════════════════════════════
#  Login Window
# ═══════════════════════════════════════════════════════════════════════════════

class LoginWindow(tk.Tk):
    """Splash login screen shown before the main app."""

    def __init__(self):
        super().__init__()
        db.init_db()

        self.title("Stock Portfolio Analyzer — Login")
        self.geometry("420x340")
        self.resizable(False, False)
        self.configure(bg=THEME["bg"])
        self._authenticated = False
        self._attempts = 0

        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=THEME["header"], height=70)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📈  Stock Portfolio Analyzer",
                 font=("Segoe UI", 15, "bold"),
                 fg=THEME["accent"], bg=THEME["header"]).pack(expand=True)

        # ── Card ────────────────────────────────────────────────────────────
        card = tk.Frame(self, bg=THEME["panel"], bd=0)
        card.pack(padx=40, pady=24, fill="both", expand=True)

        tk.Label(card, text="Welcome back", font=("Segoe UI", 13, "bold"),
                 fg=THEME["text"], bg=THEME["panel"]).pack(pady=(20, 2))
        tk.Label(card, text="Please sign in to continue",
                 font=("Segoe UI", 9), fg=THEME["sub"], bg=THEME["panel"]).pack(pady=(0, 18))

        # Username
        tk.Label(card, text="Username", font=FONT,
                 fg=THEME["sub"], bg=THEME["panel"], anchor="w").pack(fill="x", padx=24)
        self._usr = make_entry(card, width=30)
        self._usr.pack(padx=24, pady=(2, 10), fill="x")
        self._usr.insert(0, "admin")

        # Password
        tk.Label(card, text="Password", font=FONT,
                 fg=THEME["sub"], bg=THEME["panel"], anchor="w").pack(fill="x", padx=24)
        self._pwd = make_entry(card, width=30, show="*")
        self._pwd.pack(padx=24, pady=(2, 4), fill="x")
        self._pwd.bind("<Return>", lambda _: self._login())

        # Error label
        self._err_lbl = tk.Label(card, text="", font=("Segoe UI", 9),
                                  fg=THEME["red"], bg=THEME["panel"])
        self._err_lbl.pack()

        # Login button
        make_button(card, "Sign In", self._login,
                    bg=THEME["accent"]).pack(pady=(6, 20), ipadx=20)

    def _login(self):
        usr = self._usr.get().strip()
        pwd = self._pwd.get()

        if not usr or not pwd:
            self._err_lbl.config(text="Username and password are required.")
            return

        if db.verify_admin(usr, pwd):
            self._authenticated = True
            self.destroy()
        else:
            self._attempts += 1
            self._err_lbl.config(
                text=f"Invalid credentials. (Attempt {self._attempts})"
            )
            self._pwd.delete(0, "end")
            self._pwd.focus_set()


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import matplotlib.ticker   # ensure imported for formatters

    # Show login first
    login = LoginWindow()
    login.mainloop()

    # Only launch main app if login succeeded
    if login._authenticated:
        app = StockApp()
        app.mainloop()
