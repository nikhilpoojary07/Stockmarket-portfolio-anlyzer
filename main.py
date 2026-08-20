import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import datetime
import threading


import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker


import database as db
import price_fetcher
import predictor
import exporter
import importer




DARK = {
    "bg":        "#0a0a12",
    "panel":     "#14141f",
    "card":      "#1a1a2e",
    "accent":    "#8b5cf6",
    "accent2":   "#a78bfa",
    "green":     "#22c55e",
    "green_dim": "#166534",
    "red":       "#ef4444",
    "red_dim":   "#991b1b",
    "text":      "#f1f5f9",
    "text2":     "#cbd5e1",
    "sub":       "#64748b",
    "header":    "#0f0f1a",
    "border":    "#2a2a3e",
    "hover":     "#1e1e2e",
    "chart_bg":  "#14141f",
    "grid":      "#2a2a3e",
}

LIGHT = {
    "bg":        "#f8fafc",
    "panel":     "grey",
    "card":      "#f1f5f9",
    "accent":    "#7c3aed",
    "accent2":   "#8b5cf6",
    "green":     "#16a34a",
    "green_dim": "#dcfce7",
    "red":       "#dc2626",
    "red_dim":   "#fee2e2",
    "text":      "#0f172a",
    "text2":     "#334155",
    "sub":       "#64748b",
    "header":    "#e2e8f0",
    "border":    "#e2e8f0",
    "hover":     "#f1f5f9",
    "chart_bg":  "#ffffff",
    "grid":      "#e2e8f0",
}

THEME = DARK
FONT      = ("Segoe UI Variable", 10)
FONT_B    = ("Segoe UI Variable", 10, "bold")
FONT_H    = ("Segoe UI Variable", 16, "bold")
FONT_S    = ("Segoe UI Variable Semibold", 12)
FONT_XS   = ("Segoe UI Variable", 9)

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


#  Styled widgets — Modern glassmorphism aesthetic
# ═══════════════════════════════════════════════════════════════════════════════

def make_label(parent, text, font=FONT, fg=None, bg=None, **kw):
    fg = fg or THEME["text"]
    bg = bg or THEME["bg"]
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)


def make_entry(parent, width=18, **kw):
    e = tk.Entry(parent, width=width, font=FONT,
                 bg=THEME["card"], fg=THEME["text"],
                 insertbackground=THEME["accent"],
                 relief="flat", bd=6, highlightthickness=1,
                 highlightcolor=THEME["accent"],
                 highlightbackground=THEME["border"],
                 **kw)
    return e


def make_button(parent, text, command, bg=None, fg=None, hover_bg=None, **kw):
    bg = bg or THEME["accent"]
    fg = fg or "#ffffff"
    hover_bg = hover_bg or THEME["accent2"]
    
    b = tk.Button(parent, text=text, command=command,
                  bg=bg, fg=fg, font=FONT_B,
                  activebackground=hover_bg, activeforeground=fg,
                  relief="flat", padx=14, pady=6, cursor="hand2",
                  bd=0, **kw)
    
    # Store theme-specific colors on the widget itself to allow updating them dynamically
    b._normal_bg = bg
    b._hover_bg = hover_bg
    
    def on_enter(e, btn=b):
        btn.config(bg=getattr(btn, "_hover_bg", btn.cget("activebackground")))
    def on_leave(e, btn=b):
        btn.config(bg=getattr(btn, "_normal_bg", btn.cget("bg")))
    
    b.bind("<Enter>", on_enter)
    b.bind("<Leave>", on_leave)
    return b


def make_tree(parent, columns, heights=15):
    style = ttk.Style()
    style.theme_use("clam")
    
    style.configure("Custom.Treeview",
                    background=THEME["card"],
                    foreground=THEME["text"],
                    fieldbackground=THEME["card"],
                    rowheight=32,
                    font=FONT,
                    borderwidth=0)
    style.configure("Custom.Treeview.Heading",
                    background=THEME["header"],
                    foreground=THEME["text"],
                    font=FONT_B,
                    relief="flat",
                    padding=(11, 7))
    style.map("Custom.Treeview",
              background=[("selected", THEME["accent"])],
              foreground=[("selected", "#ffffff")])
    style.map("Custom.Treeview.Heading",
              background=[("active", THEME["hover"])])
    
    style.configure("Custom.Vertical.TScrollbar",
                    background=THEME["card"],
                    troughcolor=THEME["bg"],
                    bordercolor=THEME["border"],
                    arrowcolor=THEME["sub"],
                    width=12)

    tree = ttk.Treeview(parent, columns=columns, show="headings",
                        height=heights, style="Custom.Treeview")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=110)
    
    sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview,
                       style="Custom.Vertical.TScrollbar")
    tree.configure(yscrollcommand=sb.set)
    return tree, sb


def make_card(parent, title=None, padx=12, pady=12):
    """Create a modern card container with subtle border."""
    card = tk.Frame(parent, bg=THEME["card"], bd=1, relief="solid",
                    highlightbackground=THEME["border"],
                    highlightthickness=1)
    if title:
        hdr = tk.Label(card, text=f"  {title}  ", font=FONT_B,
                       fg=THEME["accent"], bg=THEME["card"])
        hdr.pack(anchor="w", padx=padx, pady=(pady//2, 0))
        tk.Frame(card, bg=THEME["border"], height=1).pack(fill="x", padx=padx, pady=4)
    return card


# ═══════════════════════════════════════════════════════════════════════════════
#  Modern Sidebar Navigation
# ═══════════════════════════════════════════════════════════════════════════════

class SidebarNav(tk.Frame):
    """Modern sidebar navigation with animated hover states."""
    
    def __init__(self, parent, commands, **kwargs):
        super().__init__(parent, bg=THEME["header"], width=200, **kwargs)
        self.pack_propagate(False)
        self.commands = commands
        self.buttons = []
        self._active_idx = 0
        
        # App title in sidebar
        title_frame = tk.Frame(self, bg=THEME["header"], height=60)
        title_frame.pack(fill="x", pady=(0, 10))
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text="📈", font=("Segoe UI", 20),
                bg=THEME["header"], fg=THEME["accent"]).pack(side="left", padx=16)
        tk.Label(title_frame, text="Portfolio\nAnalyzer", font=("Segoe UI Variable", 11, "bold"),
                bg=THEME["header"], fg=THEME["text"], justify="left").pack(side="left")
        
        # Separator
        tk.Frame(self, bg=THEME["border"], height=1).pack(fill="x", padx=12, pady=8)
        
        # Nav buttons
        self.nav_items = [
            ("📊", "Holdings"),
            ("📝", "Transactions"),
            ("👁", "Watchlist"),
            ("💰", "Dividends"),
            ("📈", "Analytics"),
            ("🔮", "Prediction"),
        ]
        
        for i, (icon, label) in enumerate(self.nav_items):
            btn = self._create_nav_button(icon, label, i)
            btn.pack(fill="x", padx=8, pady=2)
            self.buttons.append(btn)
        
        # Bottom section
        tk.Frame(self, bg=THEME["header"]).pack(expand=True, fill="both")
        
        # Theme toggle at bottom
        theme_btn = tk.Button(self, text="🌓  Toggle Theme",
                             command=self.commands.get("toggle_theme", self._toggle_theme),
                             bg=THEME["header"], fg=THEME["sub"], font=FONT,
                             relief="flat", bd=0, cursor="hand2",
                             activebackground=THEME["hover"], activeforeground=THEME["text"])
        theme_btn.pack(fill="x", padx=8, pady=8)
        
        # Refresh button
        refresh_btn = tk.Button(self, text="🔄  Refresh Prices", command=self.commands.get("refresh"),
                               bg=THEME["header"], fg=THEME["sub"], font=FONT,
                               relief="flat", bd=0, cursor="hand2",
                               activebackground=THEME["hover"], activeforeground=THEME["text"])
        refresh_btn.pack(fill="x", padx=8, pady=(0, 8))
    
    def _create_nav_button(self, icon, label, idx):
        btn = tk.Frame(self, bg=THEME["header"], height=40, cursor="hand2")
        btn.pack_propagate(False)
        
        # Active indicator bar
        indicator = tk.Frame(btn, bg=THEME["accent"] if idx == 0 else THEME["header"],
                            width=3)
        indicator.pack(side="left", fill="y")
        
        lbl = tk.Label(btn, text=f"{icon}  {label}", font=FONT_B,
                      fg=THEME["text"] if idx == 0 else THEME["sub"],
                      bg=THEME["header"], padx=12)
        lbl.pack(side="left", fill="y")
        
        def on_enter(e, b=btn, l=lbl, ind=indicator):
            if self._active_idx != idx:
                b.config(bg=THEME["hover"])
                l.config(bg=THEME["hover"])
        
        def on_leave(e, b=btn, l=lbl, ind=indicator):
            if self._active_idx != idx:
                b.config(bg=THEME["header"])
                l.config(bg=THEME["header"])
        
        def on_click(e, i=idx):
            self.set_active(i)
            cmd = self.commands.get(label.lower().replace(" ", "_"))
            if cmd:
                cmd()
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.bind("<Button-1>", on_click)
        lbl.bind("<Button-1>", on_click)
        
        btn._indicator = indicator
        btn._label = lbl
        return btn
    
    def set_active(self, idx):
        self._active_idx = idx
        for i, btn in enumerate(self.buttons):
            is_active = (i == idx)
            btn.config(bg=THEME["header"])
            btn._label.config(bg=THEME["header"],
                             fg=THEME["text"] if is_active else THEME["sub"])
            btn._indicator.config(bg=THEME["accent"] if is_active else THEME["header"])
    
    def _toggle_theme(self):
        global THEME
        THEME = LIGHT if THEME == DARK else DARK
        messagebox.showinfo("Theme Changed", 
                           "Theme toggled! Some elements will update on next refresh.\n"
                           "For full effect, restart the application.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Summary Cards Component
# ═══════════════════════════════════════════════════════════════════════════════

class SummaryCards(tk.Frame):
    """Modern summary cards with gradient-like styling."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=THEME["bg"], **kwargs)
        self.cards = {}
        self._build()
    
    def _build(self):
        metrics = [
            ("Invested", "💼", THEME["text"]),
            ("Market Value", "📊", THEME["text"]),
            ("P&L", "📈", THEME["green"]),
            ("P&L %", "📉", THEME["green"]),
            ("Day Gain", "☀️", THEME["green"]),
        ]
        
        for i, (key, icon, default_color) in enumerate(metrics):
            card = tk.Frame(self, bg=THEME["card"], bd=1, relief="solid",
                           highlightbackground=THEME["border"], highlightthickness=1)
            card.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            self.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=f"{icon}  {key}", font=FONT_XS,
                    fg=THEME["sub"], bg=THEME["card"]).pack(anchor="w", padx=14, pady=(10, 2))
            
            lbl = tk.Label(card, text="—", font=FONT_S,
                          fg=default_color, bg=THEME["card"])
            lbl.pack(anchor="w", padx=14, pady=(0, 10))
            
            self.cards[key] = lbl
    
    def update_values(self, invested, market, pnl, pnl_pct, day_gain):
        self.cards["Invested"].config(text=fmt_inr(invested), fg=THEME["text"])
        self.cards["Market Value"].config(text=fmt_inr(market), fg=THEME["text"])
        self.cards["P&L"].config(text=fmt_inr(pnl), fg=color_pnl(pnl))
        self.cards["P&L %"].config(text=f"{pnl_pct:+.2f}%", fg=color_pnl(pnl))
        self.cards["Day Gain"].config(text=fmt_inr(day_gain), fg=color_pnl(day_gain))


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Application — Modern Layout
# ═══════════════════════════════════════════════════════════════════════════════

class StockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        db.init_db()

        self.title("Stock Portfolio Analyzer")
        self.geometry("1400x900")
        self.minsize(1200, 750)
        self.configure(bg=THEME["bg"])

        self._price_cache: dict = db.get_price_cache()
        self._holdings:    dict = {}
        self._refresh_lock = threading.Lock()
        self._current_tab = "holdings"
        
        # Theme toggle states
        self._active_analytics_chart = "pie"
        self._last_pred_result = None

        self._build_ui()
        self.after(500, self._refresh_holdings_tab)

    # ── UI skeleton — Modern sidebar + content layout ─────────────────────────

    def _build_ui(self):
        # Main container
        self._main_container = tk.Frame(self, bg=THEME["bg"])
        self._main_container.pack(fill="both", expand=True)
        
        # Sidebar navigation
        self._sidebar = SidebarNav(self._main_container, {
            "holdings": lambda: self._switch_tab("holdings"),
            "transactions": lambda: self._switch_tab("transactions"),
            "watchlist": lambda: self._switch_tab("watchlist"),
            "dividends": lambda: self._switch_tab("dividends"),
            "analytics": lambda: self._switch_tab("analytics"),
            "prediction": lambda: self._switch_tab("prediction"),
            "toggle_theme": self._toggle_theme,
            "refresh": self._fetch_prices_thread,
        })
        self._sidebar.pack(side="left", fill="y")
        
        # Content area
        self._content = tk.Frame(self._main_container, bg=THEME["bg"])
        self._content.pack(side="left", fill="both", expand=True, padx=16, pady=16)
        
        # Header bar
        self._build_header()
        
        # Summary cards
        self._summary_cards = SummaryCards(self._content)
        self._summary_cards.pack(fill="x", pady=(0, 12))
        
        # Tab content container
        self._tab_container = tk.Frame(self._content, bg=THEME["bg"])
        self._tab_container.pack(fill="both", expand=True)
        
        # Build all tab frames (hidden initially)
        self._tab_frames = {}
        tab_builders = {
            "holdings":     self._build_holdings_tab,
            "transactions": self._build_transactions_tab,
            "watchlist":    self._build_watchlist_tab,
            "dividends":    self._build_dividends_tab,
            "analytics":    self._build_analytics_tab,
            "prediction":   self._build_prediction_tab,
        }
        
        for name, builder in tab_builders.items():
            frame = tk.Frame(self._tab_container, bg=THEME["bg"])
            self._tab_frames[name] = frame
            builder(frame)
        
        # Show default tab
        self._switch_tab("holdings")
    
    def _build_header(self):
        header = tk.Frame(self._content, bg=THEME["bg"], height=40)
        header.pack(fill="x", pady=(0, 8))
        header.pack_propagate(False)
        
        self._header_title = tk.Label(header, text="Portfolio Holdings",
                                     font=FONT_H, fg=THEME["text"], bg=THEME["bg"])
        self._header_title.pack(side="left")
        
        # Status indicator
        self._status_frame = tk.Frame(header, bg=THEME["bg"])
        self._status_frame.pack(side="right")
        
        self._status_dot = tk.Canvas(self._status_frame, width=8, height=8,
                                    bg=THEME["bg"], highlightthickness=0)
        self._status_dot.pack(side="left", padx=(0, 6))
        self._status_dot.create_oval(1, 1, 7, 7, fill=THEME["green"], outline="")
        
        self._status_lbl = tk.Label(self._status_frame, text="Live",
                                   font=FONT_XS, fg=THEME["green"], bg=THEME["bg"])
        self._status_lbl.pack(side="left")
    
    def _switch_tab(self, name):
        self._current_tab = name
        self._sidebar.set_active(list(self._tab_frames.keys()).index(name))
        
        # Hide all tabs
        for frame in self._tab_frames.values():
            frame.pack_forget()
        
        # Show selected tab
        self._tab_frames[name].pack(fill="both", expand=True)
        
        # Update header
        titles = {
            "holdings": "Portfolio Holdings",
            "transactions": "Transaction History",
            "watchlist": "Watchlist",
            "dividends": "Dividend Tracker",
            "analytics": "Portfolio Analytics",
            "prediction": "Price Prediction",
        }
        self._header_title.config(text=titles.get(name, name.title()))
        
        # Refresh tab content
        refresh_methods = {
            "holdings": self._refresh_holdings_tab,
            "transactions": self._refresh_txn_table,
            "watchlist": self._refresh_wl_table,
            "dividends": self._refresh_div_table,
        }
        if name in refresh_methods:
            refresh_methods[name]()

    # ── Theme Toggle & Instant UI Update ─────────────────────────────────────

    def _toggle_theme(self):
        global THEME
        old_theme = THEME
        new_theme = LIGHT if THEME == DARK else DARK
        THEME = new_theme

        # 1. Update style configurations for ttk.Treeview and ttk.Scrollbar
        self._update_styles()

        # 2. Update standard Tkinter widgets recursively starting from self (root window)
        self._update_widget_theme(self, old_theme, new_theme)

        # 3. Update the active button status inside the sidebar navigation
        self._sidebar.set_active(self._sidebar._active_idx)

        # 4. Force refresh the summary cards values using the new theme colors
        self._update_summary()

        # 5. Redraw the active chart/predict model dynamically if open
        if self._current_tab == "analytics":
            if self._active_analytics_chart == "pie":
                self._chart_pie()
            elif self._active_analytics_chart == "pnl_bar":
                self._chart_pnl_bar()
            elif self._active_analytics_chart == "nav":
                self._chart_nav()
            elif self._active_analytics_chart == "sector":
                self._chart_sector()
        elif self._current_tab == "prediction":
            if self._last_pred_result is not None:
                self._show_prediction(self._last_pred_result)

    def _update_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("Custom.Treeview",
                        background=THEME["card"],
                        foreground=THEME["text"],
                        fieldbackground=THEME["card"],
                        rowheight=32,
                        font=FONT,
                        borderwidth=0)
        style.configure("Custom.Treeview.Heading",
                        background=THEME["header"],
                        foreground=THEME["text"],
                        font=FONT_B,
                        relief="flat",
                        padding=(10, 6))
        style.map("Custom.Treeview",
                  background=[("selected", THEME["accent"])],
                  foreground=[("selected", "#ffffff")])
        style.map("Custom.Treeview.Heading",
                  background=[("active", THEME["hover"])])
        
        style.configure("Custom.Vertical.TScrollbar",
                        background=THEME["card"],
                        troughcolor=THEME["bg"],
                        bordercolor=THEME["border"],
                        arrowcolor=THEME["sub"],
                        width=12)

    def _update_widget_theme(self, widget, old_theme, new_theme):
        color_map = {}
        for k in old_theme:
            old_val = old_theme[k].lower()
            new_val = new_theme[k].lower()
            if old_val != new_val:
                color_map[old_val] = new_val

        def traverse(w):
            # Update standard Tk configurations
            for opt in ["bg", "background", "fg", "foreground", 
                        "activebackground", "activeforeground",
                        "disabledforeground", "insertbackground",
                        "highlightcolor", "highlightbackground",
                        "selectbackground", "selectforeground"]:
                try:
                    curr = w.cget(opt)
                    if curr:
                        curr_norm = str(curr).strip().lower()
                        if curr_norm in color_map:
                            w.configure(**{opt: color_map[curr_norm]})
                except tk.TclError:
                    pass

            # Update Canvas drawing elements (such as the status dot oval)
            if isinstance(w, tk.Canvas):
                for item in w.find_all():
                    for opt in ["fill", "outline"]:
                        try:
                            curr = w.itemcget(item, opt)
                            if curr:
                                curr_norm = str(curr).strip().lower()
                                if curr_norm in color_map:
                                    w.itemconfig(item, **{opt: color_map[curr_norm]})
                        except tk.TclError:
                            pass
            
            # Update Treeview tag configurations
            if isinstance(w, ttk.Treeview):
                for tag in ["profit", "loss", "buy", "sell", "near", "far"]:
                    try:
                        curr_fg = w.tag_cget(tag, "foreground")
                        if curr_fg:
                            curr_fg_norm = str(curr_fg).strip().lower()
                            if curr_fg_norm in color_map:
                                w.tag_configure(tag, foreground=color_map[curr_fg_norm])
                        
                        curr_bg = w.tag_cget(tag, "background")
                        if curr_bg:
                            curr_bg_norm = str(curr_bg).strip().lower()
                            if curr_bg_norm in color_map:
                                w.tag_configure(tag, background=color_map[curr_bg_norm])
                    except tk.TclError:
                        pass

            # Update custom normal and hover bg configurations on styled buttons
            if hasattr(w, "_normal_bg"):
                norm = str(w._normal_bg).strip().lower()
                if norm in color_map:
                    w._normal_bg = color_map[norm]
            if hasattr(w, "_hover_bg"):
                hvr = str(w._hover_bg).strip().lower()
                if hvr in color_map:
                    w._hover_bg = color_map[hvr]

            # Recurse through children
            for child in w.winfo_children():
                traverse(child)

        traverse(widget)

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

        self._summary_cards.update_values(invested, market, pnl, pnl_pct, day_gain)

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 1 — Holdings
    # ════════════════════════════════════════════════════════════════════════

    def _build_holdings_tab(self, parent):
        # Toolbar
        toolbar = tk.Frame(parent, bg=THEME["bg"])
        toolbar.pack(fill="x", pady=(0, 8))
        
        make_button(toolbar, "📥 Export CSV", self._export_holdings,
                   bg=THEME["accent"]).pack(side="right")
        
        # Table in card
        card = make_card(parent, "Holdings Overview")
        card.pack(fill="both", expand=True)
        
        cols = ("Symbol", "Qty", "Avg Cost", "LTP", "Invested", "Mkt Value", "P&L", "P&L %", "Day Gain")
        tree, sb = make_tree(card, cols, heights=22)
        tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
        sb.pack(side="left", fill="y", pady=12)

        tree.tag_configure("profit", foreground=THEME["green"])
        tree.tag_configure("loss",   foreground=THEME["red"])

        self._holdings_tree = tree

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
        form_card = make_card(parent, "Add Transaction")
        form_card.pack(fill="x", pady=(0, 12))
        
        form = tk.Frame(form_card, bg=THEME["card"])
        form.pack(fill="x", padx=12, pady=12)

        fields = [("Symbol", 12), ("Type (BUY/SELL)", 10), ("Qty", 10),
                  ("Price ₹", 10), ("Brokerage ₹", 10), ("Date (YYYY-MM-DD)", 14)]
        self._txn_entries = {}
        for i, (label, w) in enumerate(fields):
            tk.Label(form, text=label, font=FONT, bg=THEME["card"], fg=THEME["sub"]).grid(
                row=0, column=i * 2, padx=(12, 4), pady=8)
            e = make_entry(form, width=w)
            e.grid(row=0, column=i * 2 + 1, padx=(0, 8))
            self._txn_entries[label] = e

        self._txn_entries["Date (YYYY-MM-DD)"].insert(0, today())

        bf = tk.Frame(form, bg=THEME["card"])
        bf.grid(row=0, column=len(fields) * 2, padx=8)
        make_button(bf, "➕ Add", self._add_transaction, bg=THEME["green"]).pack(side="left", padx=4)
        make_button(bf, "🗑 Delete", self._delete_transaction, bg=THEME["red"]).pack(side="left")
        make_button(bf, "📥 Import CSV", self._import_transactions_csv, bg=THEME["accent"]).pack(side="left", padx=4)

        table_card = make_card(parent, "Transaction History")
        table_card.pack(fill="both", expand=True)
        
        cols = ("ID", "Symbol", "Type", "Qty", "Price", "Brokerage", "Date")
        tree, sb = make_tree(table_card, cols, heights=18)
        tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
        sb.pack(side="left", fill="y", pady=12)
        tree.tag_configure("buy",  foreground=THEME["green"])
        tree.tag_configure("sell", foreground=THEME["red"])
        self._txn_tree = tree
        self._refresh_txn_table()

        make_button(parent, "📥 Export CSV", self._export_transactions,
                   bg=THEME["accent"]).pack(pady=12, anchor="e")

    def _refresh_txn_table(self, symbol=None):
        tree = self._txn_tree
        tree.delete(*tree.get_children())
        for row in db.get_transactions(symbol):
            tag = "buy" if row[2] == "BUY" else "sell"
            tree.insert("", "end", values=row, tags=(tag,))

    def _validate_stock_price(self, sym: str, entered_price: float) -> float:
        try:
            live_prices = price_fetcher.fetch_prices([sym])
            if sym not in live_prices or not live_prices[sym]:
                return entered_price
            live_price = live_prices[sym].get("ltp", 0)
            if live_price <= 0:
                return entered_price
            pct_diff = abs((entered_price - live_price) / live_price) * 100
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
                if response == "retry":
                    messagebox.showinfo("Price Updated", f"Using live trading price: ₹{live_price:.2f}")
                    return live_price
                else:
                    return entered_price
            return entered_price
        except Exception as e:
            print(f"Price validation error: {e}")
            return entered_price
    
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

        stocks = {s[0] for s in db.get_all_stocks()}
        if sym not in stocks:
            db.add_stock(sym, sym, "Unknown", "NSE")

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
        form_card = make_card(parent, "Add to Watchlist")
        form_card.pack(fill="x", pady=(0, 12))
        
        form = tk.Frame(form_card, bg=THEME["card"])
        form.pack(fill="x", padx=12, pady=12)

        self._wl_entries = {}
        for i, (lbl, w) in enumerate([("Symbol", 10), ("Company", 20), ("Target ₹", 10)]):
            tk.Label(form, text=lbl, font=FONT, bg=THEME["card"], fg=THEME["sub"]).grid(
                row=0, column=i * 2, padx=12, pady=8)
            e = make_entry(form, width=w)
            e.grid(row=0, column=i * 2 + 1)
            self._wl_entries[lbl] = e

        bf = tk.Frame(form, bg=THEME["card"])
        bf.grid(row=0, column=6, padx=10)
        make_button(bf, "➕ Add", self._add_watchlist, bg=THEME["green"]).pack(side="left", padx=4)
        make_button(bf, "🗑 Remove", self._del_watchlist, bg=THEME["red"]).pack(side="left")
        make_button(bf, "📥 Import CSV", self._import_watchlist_csv, bg=THEME["accent"]).pack(side="left", padx=4)

        table_card = make_card(parent, "Watchlist")
        table_card.pack(fill="both", expand=True)
        
        cols = ("ID", "Symbol", "Company", "Target ₹", "LTP", "Gap %", "Added")
        tree, sb = make_tree(table_card, cols, heights=18)
        tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
        sb.pack(side="left", fill="y", pady=12)
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
        form_card = make_card(parent, "Log Dividend")
        form_card.pack(fill="x", pady=(0, 12))
        
        form = tk.Frame(form_card, bg=THEME["card"])
        form.pack(fill="x", padx=12, pady=12)

        self._div_entries = {}
        for i, (lbl, w) in enumerate([("Symbol", 10), ("₹ / Share", 10),
                                       ("Qty", 10), ("Date", 12)]):
            tk.Label(form, text=lbl, font=FONT, bg=THEME["card"], fg=THEME["sub"]).grid(
                row=0, column=i * 2, padx=12, pady=8)
            e = make_entry(form, width=w)
            e.grid(row=0, column=i * 2 + 1)
            self._div_entries[lbl] = e
        self._div_entries["Date"].insert(0, today())

        bf = tk.Frame(form, bg=THEME["card"])
        bf.grid(row=0, column=8, padx=10)
        make_button(bf, "➕ Add", self._add_dividend, bg=THEME["green"]).pack(side="left", padx=4)
        make_button(bf, "🗑 Delete", self._del_dividend, bg=THEME["red"]).pack(side="left")
        make_button(bf, "📥 Import CSV", self._import_dividends_csv, bg=THEME["accent"]).pack(side="left", padx=4)

        table_card = make_card(parent, "Dividend History")
        table_card.pack(fill="both", expand=True)
        
        cols = ("ID", "Symbol", "₹/Share", "Qty", "Total", "Date")
        tree, sb = make_tree(table_card, cols, heights=16)
        tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
        sb.pack(side="left", fill="y", pady=12)
        self._div_tree = tree
        self._refresh_div_table()

        # Total income label
        self._div_total_lbl = tk.Label(parent, text="Total Dividend Income: ₹0.00",
                                        font=FONT_B, bg=THEME["bg"], fg=THEME["green"])
        self._div_total_lbl.pack(pady=8)

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
        btn_row.pack(fill="x", pady=(0, 12))

        make_button(btn_row, "🥧 Allocation Pie",    self._chart_pie).pack(side="left", padx=6)
        make_button(btn_row, "📊 P&L Bar",           self._chart_pnl_bar).pack(side="left", padx=6)
        make_button(btn_row, "📈 NAV Trend",          self._chart_nav).pack(side="left", padx=6)
        make_button(btn_row, "🏭 Sector Breakdown",   self._chart_sector).pack(side="left", padx=6)

        chart_card = make_card(parent, "Chart Visualization")
        chart_card.pack(fill="both", expand=True)
        
        self._analytics_canvas_frame = tk.Frame(chart_card, bg=THEME["card"])
        self._analytics_canvas_frame.pack(fill="both", expand=True, padx=12, pady=12)
        self._chart_pie()

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
        self._active_analytics_chart = "pie"
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
        fig = Figure(figsize=(10, 6), facecolor=THEME["chart_bg"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(THEME["chart_bg"])
        
        colors = plt.cm.Set3(range(len(labels)))
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct="%1.1f%%",
            startangle=140, colors=colors,
            textprops={"color": THEME["text"], "fontsize": 10},
            pctdistance=0.75
        )
        for w in wedges:
            w.set_edgecolor(THEME["border"])
            w.set_linewidth(1.5)
        ax.set_title("Portfolio Allocation by Market Value",
                     color=THEME["text"], fontsize=14, pad=16, fontweight="bold")
        self._embed_fig(fig)

    def _chart_pnl_bar(self):
        self._active_analytics_chart = "pnl_bar"
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
        fig = Figure(figsize=(10, 6), facecolor=THEME["chart_bg"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(THEME["chart_bg"])
        bars = ax.bar(syms, pnls, color=colors, edgecolor=THEME["border"], linewidth=1)
        ax.axhline(0, color=THEME["sub"], linewidth=0.8)
        ax.set_title("Unrealised P&L per Stock", color=THEME["text"], fontsize=14, fontweight="bold")
        ax.tick_params(colors=THEME["text"])
        ax.set_ylabel("P&L (₹)", color=THEME["text"])
        for spine in ax.spines.values():
            spine.set_edgecolor(THEME["border"])
        ax.grid(axis="y", alpha=0.2, color=THEME["grid"])
        self._embed_fig(fig)

    def _chart_nav(self):
        self._active_analytics_chart = "nav"
        txns = db.get_transactions()
        if not txns:
            messagebox.showinfo("No Data", "No transactions found.")
            return
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
        fig = Figure(figsize=(10, 6), facecolor=THEME["chart_bg"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(THEME["chart_bg"])
        ax.plot([datetime.date.fromisoformat(d) for d in dates_sorted],
                cum, color=THEME["accent"], linewidth=2.5, marker="o", markersize=5)
        ax.fill_between([datetime.date.fromisoformat(d) for d in dates_sorted],
                        cum, alpha=0.15, color=THEME["accent"])
        ax.set_title("Portfolio NAV Trend (Cumulative Invested)", 
                    color=THEME["text"], fontsize=14, fontweight="bold")
        ax.tick_params(colors=THEME["text"])
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
        for spine in ax.spines.values():
            spine.set_edgecolor(THEME["border"])
        ax.grid(alpha=0.2, color=THEME["grid"])
        self._embed_fig(fig)

    def _chart_sector(self):
        self._active_analytics_chart = "sector"
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
        fig = Figure(figsize=(10, 6), facecolor=THEME["chart_bg"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(THEME["chart_bg"])
        colors = plt.cm.Pastel1(range(len(labels)))
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90,
               textprops={"color": THEME["text"], "fontsize": 10},
               colors=colors)
        ax.set_title("Sector-wise Allocation", color=THEME["text"], fontsize=14, fontweight="bold")
        self._embed_fig(fig)

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 6 — Prediction
    # ════════════════════════════════════════════════════════════════════════

    def _build_prediction_tab(self, parent):
        # Header
        header_card = make_card(parent, "ML Stock Price Prediction")
        header_card.pack(fill="x", pady=(0, 12))
        
        hdr = tk.Frame(header_card, bg=THEME["card"])
        hdr.pack(fill="x", padx=12, pady=12)
        
        tk.Label(hdr, text="🤖  Linear Regression + Technical Indicators",
                font=("Segoe UI Variable", 11), bg=THEME["card"], fg=THEME["sub"]).pack(anchor="w")
        tk.Label(hdr, text="Features: MA7 · MA21 · MA50 · RSI · Momentum · Volatility",
                font=FONT_XS, bg=THEME["card"], fg=THEME["sub"]).pack(anchor="w", pady=(4, 0))

        # Controls
        ctrl_card = make_card(parent)
        ctrl_card.pack(fill="x", pady=(0, 12))
        
        ctrl = tk.Frame(ctrl_card, bg=THEME["card"])
        ctrl.pack(padx=12, pady=12)
        
        tk.Label(ctrl, text="Symbol:", font=FONT, bg=THEME["card"], fg=THEME["sub"]).pack(side="left")
        self._pred_sym = make_entry(ctrl, width=12)
        self._pred_sym.pack(side="left", padx=6)

        tk.Label(ctrl, text="Days Ahead:", font=FONT, bg=THEME["card"], fg=THEME["sub"]).pack(side="left")
        self._pred_days = make_entry(ctrl, width=6)
        self._pred_days.insert(0, "7")
        self._pred_days.pack(side="left", padx=6)

        make_button(ctrl, "🔮 Predict", self._run_prediction,
                   bg=THEME["accent"]).pack(side="left", padx=10)

        # Result info panel
        info_card = make_card(parent, "Prediction Results")
        info_card.pack(fill="x", pady=(0, 12))
        
        self._pred_info = tk.Frame(info_card, bg=THEME["card"])
        self._pred_info.pack(fill="x", padx=12, pady=12)
        self._pred_info_labels = {}
        info_keys = ["Current Price", "Predicted Price", "Direction",
                     "Change %", "Confidence", "Back-test MAPE",
                     "MA7", "MA21", "RSI"]
        for i, k in enumerate(info_keys):
            col = i % 3
            row = i // 3
            f = tk.Frame(self._pred_info, bg=THEME["card"])
            f.grid(row=row, column=col, padx=20, pady=8, sticky="w")
            tk.Label(f, text=k, font=FONT_XS,
                     bg=THEME["card"], fg=THEME["sub"]).pack(anchor="w")
            lbl = tk.Label(f, text="—", font=FONT_B,
                           bg=THEME["card"], fg=THEME["text"])
            lbl.pack(anchor="w")
            self._pred_info_labels[k] = lbl

        # Chart area
        chart_card = make_card(parent, "Forecast Chart")
        chart_card.pack(fill="both", expand=True)
        
        self._pred_chart_frame = tk.Frame(chart_card, bg=THEME["card"])
        self._pred_chart_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Status
        self._pred_status = tk.Label(parent, text="Enter a symbol and click Predict.",
                                      font=FONT, bg=THEME["bg"], fg=THEME["sub"])
        self._pred_status.pack(pady=8)

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

        self._last_pred_result = r
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

        fig = Figure(figsize=(10, 5), facecolor=THEME["chart_bg"])
        ax  = fig.add_subplot(111)
        ax.set_facecolor(THEME["chart_bg"])

        # Historical last 3 months
        hist_df = price_fetcher.fetch_history(sym, period="3mo")
        if hist_df is not None and not hist_df.empty:
            hist_close = hist_df["Close"].squeeze()
            hist_dates = [d.date() if hasattr(d, "date") else d for d in hist_df.index]
            ax.plot(hist_dates, hist_close,
                    color=THEME["sub"], linewidth=1.5, label="Historical", alpha=0.7)

        ax.plot(dates, prices, color=THEME["accent"],
                linewidth=2.5, marker="o", markersize=5,
                linestyle="--", label=f"Forecast ({len(series)}d)")
        ax.fill_between(dates, prices, alpha=0.12, color=THEME["accent"])
        ax.axhline(r["current_price"], color=THEME["text"],
                   linewidth=0.8, linestyle=":", alpha=0.5)

        ax.set_title(f"{sym} — {len(series)}-Day Price Forecast",
                     color=THEME["text"], fontsize=13, fontweight="bold")
        ax.tick_params(colors=THEME["text"])
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.legend(facecolor=THEME["panel"], labelcolor=THEME["text"], edgecolor=THEME["border"])
        ax.grid(alpha=0.2, color=THEME["grid"])
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
        
        # Update status indicator to "updating"
        self._status_dot.delete("all")
        self._status_dot.create_oval(1, 1, 7, 7, fill="#f59e0b", outline="")
        self._status_lbl.config(text="Updating...", fg="#f59e0b")
        self.update_idletasks()

        def worker():
            result = price_fetcher.fetch_prices(symbols)
            self._price_cache.update(result)
            self.after(0, self._refresh_holdings_tab)
            self.after(0, self._refresh_wl_table)
            self.after(0, self._update_status_done)

        threading.Thread(target=worker, daemon=True).start()
    
    def _update_status_done(self):
        self._status_dot.delete("all")
        self._status_dot.create_oval(1, 1, 7, 7, fill=THEME["green"], outline="")
        self._status_lbl.config(text="Live", fg=THEME["green"])

    # ════════════════════════════════════════════════════════════════════════
    #  Admin panel
    # ════════════════════════════════════════════════════════════════════════

    def _admin_login(self):
        win = tk.Toplevel(self)
        win.title("Admin Login")
        win.configure(bg=THEME["bg"])
        win.geometry("380x260")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        card = tk.Frame(win, bg=THEME["card"], bd=1, relief="solid",
                       highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(padx=24, pady=24, fill="both", expand=True)

        tk.Label(card, text="🔐 Admin Login", font=FONT_H,
                 bg=THEME["card"], fg=THEME["accent"]).pack(pady=(16, 14))

        form = tk.Frame(card, bg=THEME["card"])
        form.pack(padx=20)
        
        tk.Label(form, text="Username:", font=FONT, bg=THEME["card"], fg=THEME["sub"]).grid(row=0, column=0, padx=8, pady=6, sticky="e")
        usr = make_entry(form, width=20)
        usr.grid(row=0, column=1, pady=6)
        usr.insert(0, "admin")

        tk.Label(form, text="Password:", font=FONT, bg=THEME["card"], fg=THEME["sub"]).grid(row=1, column=0, padx=8, pady=6, sticky="e")
        pwd = make_entry(form, width=20, show="*")
        pwd.grid(row=1, column=1, pady=6)
        pwd.bind("<Return>", lambda _: login())

        def login():
            if db.verify_admin(usr.get(), pwd.get()):
                win.destroy()
                self._admin_dashboard()
            else:
                messagebox.showerror("Error", "Invalid credentials.", parent=win)

        make_button(card, "Login", login, bg=THEME["accent"]).pack(pady=(14, 16), ipadx=20)

    def _admin_dashboard(self):
        win = tk.Toplevel(self)
        win.title("Admin Dashboard")
        win.configure(bg=THEME["bg"])
        win.geometry("750x580")
        win.transient(self)

        tk.Label(win, text="🔐 Admin Dashboard", font=FONT_H,
                 bg=THEME["bg"], fg=THEME["accent"]).pack(pady=(16, 12))

        btn_f = tk.Frame(win, bg=THEME["bg"])
        btn_f.pack(pady=8)

        make_button(btn_f, "📋 View All Stocks",   lambda: self._admin_stocks(win)).pack(side="left", padx=8)
        make_button(btn_f, "➕ Add Stock",          lambda: self._admin_add_stock(win)).pack(side="left", padx=8)
        make_button(btn_f, "📥 Backup DB to CSV",  self._export_full_backup).pack(side="left", padx=8)

        table_card = make_card(win, "Stock Database")
        table_card.pack(fill="both", expand=True, padx=16, pady=8)
        
        f = tk.Frame(table_card, bg=THEME["card"])
        f.pack(fill="both", expand=True, padx=12, pady=12)
        
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
                    bg=THEME["red"]).pack(pady=12)

    def _admin_stocks(self, parent):
        parent._refresh()

 
         def _admin_add_stock(self, parent):
        win = tk.Toplevel(parent)
        win.title("Add Stock")
        win.configure(bg=THEME["bg"])
        win.geometry("450x330")
        win.transient(parent)
        win.grab_set()

        card = tk.Frame(win, bg=THEME["card"], bd=1, relief="solid",
                       highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(padx=20, pady=20, fill="both", expand=True)

        tk.Label(card, text="➕ Add New Stock", font=FONT_H,
                bg=THEME["card"], fg=THEME["accent"]).pack(pady=(16, 12))

        entries = {}
        form = tk.Frame(card, bg=THEME["card"])
        form.pack(padx=16)
        
        # Row 0: Symbol with Fetch Button
        tk.Label(form, text="Symbol", font=FONT, bg=THEME["card"], fg=THEME["sub"]).grid(row=0, column=0, padx=10, pady=8, sticky="e")
        sym_frame = tk.Frame(form, bg=THEME["card"])
        sym_frame.grid(row=0, column=1, pady=8, sticky="w")
        
        e_sym = make_entry(sym_frame, width=14)
        e_sym.pack(side="left", padx=(0, 6))
        entries["Symbol"] = e_sym

        # Row 1: Company
        tk.Label(form, text="Company", font=FONT, bg=THEME["card"], fg=THEME["sub"]).grid(row=1, column=0, padx=10, pady=8, sticky="e")
        e_comp = make_entry(form, width=24)
        e_comp.grid(row=1, column=1, pady=8, sticky="w")
        entries["Company"] = e_comp

        # Row 2: Sector
        tk.Label(form, text="Sector", font=FONT, bg=THEME["card"], fg=THEME["sub"]).grid(row=2, column=0, padx=10, pady=8, sticky="e")
        e_sec = make_entry(form, width=24)
        e_sec.insert(0, "Unknown")
        e_sec.grid(row=2, column=1, pady=8, sticky="w")
        entries["Sector"] = e_sec

        # Row 3: Exchange
        tk.Label(form, text="Exchange", font=FONT, bg=THEME["card"], fg=THEME["sub"]).grid(row=3, column=0, padx=10, pady=8, sticky="e")
        e_exc = make_entry(form, width=24)
        e_exc.insert(0, "NSE")
        e_exc.grid(row=3, column=1, pady=8, sticky="w")
        entries["Exchange"] = e_exc

        def auto_fill():
            sym = e_sym.get().strip().upper()
            if not sym:
                messagebox.showerror("Error", "Please enter a symbol first.", parent=win)
                return
            
            btn_fetch.config(text="Fetching...", state="disabled")
            
            def worker():
                info = price_fetcher.fetch_info(sym)
                
                def update_ui():
                    btn_fetch.config(text="🔍 Fetch", state="normal")
                    if info.get("error"):
                        messagebox.showerror("Error", f"Could not fetch details: {info['error']}", parent=win)
                    else:
                        e_comp.delete(0, tk.END)
                        e_comp.insert(0, info.get("company", ""))
                        
                        e_sec.delete(0, tk.END)
                        e_sec.insert(0, info.get("sector", "Unknown"))
                        
                        # Determine exchange based on suffix or default
                        exc_val = "NSE"
                        if "." in sym:
                            suffix = sym.split(".")[-1]
                            if suffix == "NS":
                                exc_val = "NSE"
                            elif suffix == "BO":
                                exc_val = "BSE"
                            else:
                                exc_val = suffix
                        
                        e_exc.delete(0, tk.END)
                        e_exc.insert(0, exc_val)
                        
                        messagebox.showinfo("Success", f"Retrieved details for {sym}!", parent=win)
                
                win.after(0, update_ui)

            threading.Thread(target=worker, daemon=True).start()

        btn_fetch = make_button(sym_frame, "🔍 Fetch", auto_fill, bg=THEME["accent"])
        btn_fetch.config(font=FONT_XS, padx=6, pady=2)
        btn_fetch.pack(side="left")

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

        make_button(card, "💾 Save", save, bg=THEME["green"]).pack(pady=(12, 16), ipadx=20) 
    
    def _import_watchlist_csv(self):
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
        status_msg = csv_importer.get_status_message()
        messagebox.showinfo(f"{data_type} Import Complete", status_msg)
        self._refresh_txn_table()
        self._refresh_wl_table()
        self._refresh_div_table()
        self._refresh_holdings_tab()

    def _export_full_backup(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            exporter.export_transactions(path)
            messagebox.showinfo("Done", f"Exported to {path}")

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
#  Modern Login Window
# ═══════════════════════════════════════════════════════════════════════════════

class LoginWindow(tk.Tk):
    """Modern splash login screen with glassmorphism card."""

    def __init__(self):
        super().__init__()
        db.init_db()

        self.title("Stock Portfolio Analyzer — Login")
        self.geometry("480x420")
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
        # Decorative top bar
        top_bar = tk.Frame(self, bg=THEME["accent"], height=4)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        # Main content
        main = tk.Frame(self, bg=THEME["bg"])
        main.pack(fill="both", expand=True, padx=40, pady=30)

        # Logo / Icon
        logo_frame = tk.Frame(main, bg=THEME["bg"])
        logo_frame.pack(pady=(0, 16))
        
        logo = tk.Label(logo_frame, text="📈", font=("Segoe UI", 48),
                       bg=THEME["bg"], fg=THEME["accent"])
        logo.pack()

        # Title
        tk.Label(main, text="Stock Portfolio Analyzer",
                font=("Segoe UI Variable", 18, "bold"),
                fg=THEME["text"], bg=THEME["bg"]).pack()
        
        tk.Label(main, text="Sign in to manage your portfolio",
                font=FONT, fg=THEME["sub"], bg=THEME["bg"]).pack(pady=(4, 24))

        # Login card
        card = tk.Frame(main, bg=THEME["card"], bd=1, relief="solid",
                       highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(fill="x", padx=0, pady=0)

        # Username
        tk.Label(card, text="Username", font=FONT_B,
                fg=THEME["sub"], bg=THEME["card"], anchor="w").pack(fill="x", padx=16, pady=(16, 4))
        self._usr = make_entry(card, width=30)
        self._usr.pack(padx=16, pady=(0, 12), fill="x")
        self._usr.insert(0, "admin")

        # Password
        tk.Label(card, text="Password", font=FONT_B,
                fg=THEME["sub"], bg=THEME["card"], anchor="w").pack(fill="x", padx=16, pady=(4, 4))
        self._pwd = make_entry(card, width=30, show="*")
        self._pwd.pack(padx=16, pady=(0, 4), fill="x")
        self._pwd.bind("<Return>", lambda _: self._login())

        # Error label
        self._err_lbl = tk.Label(card, text="", font=FONT_XS,
                                  fg=THEME["red"], bg=THEME["card"])
        self._err_lbl.pack(pady=(0, 8))

        # Login button
        make_button(card, "Sign In →", self._login,
                   bg=THEME["accent"]).pack(pady=(0, 16), padx=16, fill="x")

        # Footer hint
        tk.Label(main, text="Default: admin / admin",
                font=FONT_XS, fg=THEME["sub"], bg=THEME["bg"]).pack(pady=(16, 0))

    def _login(self):
        usr = self._usr.get().strip()
        pwd = self._pwd.get()

        if not usr or not pwd:
            self._err_lbl.config(text="⚠ Username and password are required.")
            return

        if db.verify_admin(usr, pwd):
            self._authenticated = True
            self.destroy()
        else:
            self._attempts += 1
            self._err_lbl.config(
                text=f"❌ Invalid credentials. (Attempt {self._attempts})"
            )
            self._pwd.delete(0, "end")
            self._pwd.focus_set()


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import matplotlib.ticker

    # Show login first
    login = LoginWindow()
    login.mainloop()

    # Only launch main app if login succeeded
    if login._authenticated:
        app = StockApp()
        app.mainloop()
