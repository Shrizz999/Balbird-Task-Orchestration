import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Dict, Any, Optional
import os
from PIL import Image, ImageTk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import Counter

# --- Styling Constants ---
BG_COLOR = "#f4f6f9"
CARD_BG = "#ffffff"
TEXT_COLOR = "#1e293b"
TEXT_MUTED = "#64748b"
ACCENT_COLOR = "#0ea5e9"
BORDER_COLOR = "#e2e8f0"

# Chart palette – muted professional tones
CHART_COLORS = ["#0ea5e9", "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6"]

FONT_MAIN = ("Inter", 12)
FONT_BOLD = ("Inter", 12, "bold")
FONT_TITLE = ("Inter", 16, "bold")
FONT_H1 = ("Inter", 24, "bold")
FONT_SMALL = ("Inter", 10)


class DashboardStyles:
    _applied = False

    @classmethod
    def apply_treeview_style(cls):
        if cls._applied:
            return
        cls._applied = True
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=CARD_BG, foreground=TEXT_COLOR,
                        rowheight=30, fieldbackground=CARD_BG,
                        font=FONT_MAIN, borderwidth=0)
        style.map("Treeview",
                  background=[("selected", "#e0f2fe")],
                  foreground=[("selected", TEXT_COLOR)])
        style.configure("Treeview.Heading",
                        background=BG_COLOR, foreground=TEXT_MUTED,
                        font=FONT_BOLD, borderwidth=0, relief="flat")
        style.map("Treeview.Heading", background=[("active", BORDER_COLOR)])

    @classmethod
    def apply_tags(cls, tree: ttk.Treeview):
        tree.tag_configure("status_completed", foreground="#10b981") # Green
        tree.tag_configure("status_pending", foreground="#f59e0b") # Orange
        tree.tag_configure("status_delayed", foreground="#ef4444") # Red
        tree.tag_configure("row", foreground=TEXT_COLOR)


class KPICard(ctk.CTkFrame):
    def __init__(self, master, title: str, value: str, subtitle: str = "", clickable: bool = False, command: Callable = None, **kwargs):
        super().__init__(master, fg_color=CARD_BG, border_width=1,
                         border_color=BORDER_COLOR, corner_radius=6, **kwargs)

        self.lbl_title = ctk.CTkLabel(self, text=title, font=FONT_BOLD, text_color=TEXT_MUTED)
        self.lbl_title.pack(anchor="w", padx=15, pady=(12, 0))

        self.lbl_value = ctk.CTkLabel(self, text=value, font=FONT_H1, text_color=TEXT_COLOR)
        self.lbl_value.pack(anchor="w", padx=15, pady=(2, 0))

        if subtitle:
            self.lbl_sub = ctk.CTkLabel(self, text=subtitle, font=FONT_SMALL, text_color=TEXT_MUTED)
            self.lbl_sub.pack(anchor="w", padx=15, pady=(0, 10))
        else:
            self.lbl_value.pack_configure(pady=(2, 12))

        if clickable and command:
            self.configure(cursor="hand2")
            self.bind("<Button-1>", lambda e: command())
            self.lbl_title.bind("<Button-1>", lambda e: command())
            self.lbl_value.bind("<Button-1>", lambda e: command())
            if hasattr(self, 'lbl_sub'):
                self.lbl_sub.bind("<Button-1>", lambda e: command())

    def set_value(self, value: str):
        self.lbl_value.configure(text=value)


class ChartCard(ctk.CTkFrame):
    """Embeds a matplotlib chart inside a CustomTkinter card."""

    def __init__(self, master, title: str, fig_width: float = 4.0, fig_height: float = 2.8, **kwargs):
        super().__init__(master, fg_color=CARD_BG, border_width=1,
                         border_color=BORDER_COLOR, corner_radius=6, **kwargs)
        self.title = title

        self.lbl_title = ctk.CTkLabel(self, text=title, font=FONT_BOLD, text_color=TEXT_COLOR)
        self.lbl_title.pack(anchor="w", padx=15, pady=(12, 0))

        self.fig = Figure(figsize=(fig_width, fig_height), dpi=96, facecolor=CARD_BG)
        self.ax = self.fig.add_subplot(111)
        self._style_ax()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(5, 10))

    def _style_ax(self):
        self.ax.set_facecolor(CARD_BG)
        self.ax.tick_params(colors=TEXT_MUTED, labelsize=8)
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_color(BORDER_COLOR)
        self.ax.spines["bottom"].set_color(BORDER_COLOR)

    def clear(self):
        self.ax.clear()
        self._style_ax()

    def draw(self):
        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()

    def bar_chart(self, labels: List[str], values: List[float], color: str = None, horizontal: bool = False):
        self.clear()
        colors = color if isinstance(color, list) else [color or ACCENT_COLOR] * len(labels)
        if horizontal:
            self.ax.barh(labels, values, color=colors, height=0.6)
            self.ax.invert_yaxis()
        else:
            self.ax.bar(labels, values, color=colors, width=0.6)
        self.draw()

    def pie_chart(self, labels: List[str], values: List[float], colors: List[str] = None):
        self.clear()
        use_colors = colors or CHART_COLORS[:len(labels)]
        wedges, texts, autotexts = self.ax.pie(
            values, labels=labels, colors=use_colors,
            autopct='%1.0f%%', startangle=90, textprops={"fontsize": 8, "color": TEXT_COLOR}
        )
        for t in autotexts:
            t.set_fontsize(7)
            t.set_color("white")
        self.ax.set_aspect("equal")
        self.draw()

    def line_chart(self, x_labels: List[str], datasets: Dict[str, List[float]]):
        self.clear()
        for idx, (label, values) in enumerate(datasets.items()):
            c = CHART_COLORS[idx % len(CHART_COLORS)]
            self.ax.plot(x_labels[:len(values)], values, marker="o", markersize=4, linewidth=1.5, label=label, color=c)
        self.ax.legend(fontsize=7, frameon=False, labelcolor=TEXT_MUTED)
        self.ax.tick_params(axis='x', rotation=30)
        self.draw()

    def stacked_bar_chart(self, labels: List[str], datasets: Dict[str, List[float]], colors: List[str] = None):
        """Stacked vertical bar chart. datasets = {"Pending": [3,2,1], "Completed": [1,4,2]}"""
        self.clear()
        use_colors = colors or CHART_COLORS
        bottom = [0] * len(labels)
        for idx, (series_name, values) in enumerate(datasets.items()):
            c = use_colors[idx % len(use_colors)]
            self.ax.bar(labels, values, bottom=bottom, color=c, width=0.55, label=series_name)
            bottom = [b + v for b, v in zip(bottom, values)]
        self.ax.legend(fontsize=7, frameon=False, labelcolor=TEXT_MUTED, loc="upper right")
        self.draw()

    def horizontal_stacked_bar_chart(self, labels: List[str], datasets: Dict[str, List[float]], colors: List[str] = None):
        """Stacked horizontal bar chart."""
        self.clear()
        use_colors = colors or CHART_COLORS
        left = [0] * len(labels)
        for idx, (series_name, values) in enumerate(datasets.items()):
            c = use_colors[idx % len(use_colors)]
            self.ax.barh(labels, values, left=left, color=c, height=0.55, label=series_name)
            left = [l + v for l, v in zip(left, values)]
        self.ax.invert_yaxis()
        self.ax.legend(fontsize=7, frameon=False, labelcolor=TEXT_MUTED, loc="lower right")
        self.draw()


class DataTable(ctk.CTkFrame):
    def __init__(self, master, columns: List[Dict[str, Any]], data: List[Dict[str, Any]] = None,
                 double_click_callback: Callable = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.double_click_callback = double_click_callback
        self.columns = columns
        self.data = data or []

        DashboardStyles.apply_treeview_style()

        self.vsb = ttk.Scrollbar(self, orient="vertical")
        self.vsb.pack(side="right", fill="y")
        self.hsb = ttk.Scrollbar(self, orient="horizontal")
        self.hsb.pack(side="bottom", fill="x")

        col_ids = [c["id"] for c in columns]
        self.tree = ttk.Treeview(self, columns=col_ids, show="headings",
                                 yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        self.vsb.config(command=self.tree.yview)
        self.hsb.config(command=self.tree.xview)

        for col in columns:
            self.tree.heading(col["id"], text=col["title"],
                              command=lambda c=col["id"]: self._sort_column(c, False))
            self.tree.column(col["id"], width=col.get("width", 100), anchor=col.get("anchor", "w"))

        self.tree.pack(side="left", fill="both", expand=True)

        if self.double_click_callback:
            self.tree.bind("<Double-1>", self._on_double_click)

        self._load_data(self.data)

    def _load_data(self, data: List[Dict[str, Any]]):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        DashboardStyles.apply_tags(self.tree)
        
        for i, row_data in enumerate(data):
            values = [row_data.get(c["id"], "") for c in self.columns]
            
            tag = "row"
            status = str(row_data.get("status", "")).lower()
            if status:
                if "completed" in status or "done" in status:
                    tag = "status_completed"
                elif "delayed" in status or "overdue" in status:
                    tag = "status_delayed"
                elif "pending" in status or "in progress" in status:
                    tag = "status_pending"
                    
            self.tree.insert("", "end", iid=str(i), values=values, tags=(tag,))

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.data = new_data
        self._load_data(self.data)

    def _on_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item_id = sel[0]
        try:
            idx = int(item_id)
            if 0 <= idx < len(self.data):
                self.double_click_callback(self.data[idx])
        except ValueError:
            values = self.tree.item(item_id, "values")
            row_dict = {}
            for idx, col in enumerate(self.columns):
                row_dict[col["id"]] = values[idx] if idx < len(values) else ""
            self.double_click_callback(row_dict)

    def _sort_column(self, col_id, reverse):
        items = [(self.tree.set(k, col_id), k) for k in self.tree.get_children("")]
        items.sort(reverse=reverse)
        for index, (val, k) in enumerate(items):
            self.tree.move(k, "", index)
        self.tree.heading(col_id, command=lambda: self._sort_column(col_id, not reverse))


class ModernCardTable(ctk.CTkScrollableFrame):
    def __init__(self, master, columns: List[Dict[str, Any]], data: List[Dict[str, Any]] = None,
                 double_click_callback: Callable = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.double_click_callback = double_click_callback
        self.columns = columns
        self.data = data or []
        
        self._build_header()
        self.rows_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.rows_frame.pack(fill="both", expand=True)
        self._load_data(self.data)

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10), padx=5)
        for i, col in enumerate(self.columns):
            weight = col.get("weight", 1)
            header_frame.grid_columnconfigure(i, weight=int(weight*10), uniform="col")
            lbl = ctk.CTkLabel(header_frame, text=col["title"].upper(), font=FONT_BOLD, text_color=TEXT_MUTED, anchor="w")
            lbl.grid(row=0, column=i, sticky="w", padx=10)

    def _load_data(self, data):
        for widget in self.rows_frame.winfo_children():
            widget.destroy()
        
        for row_data in data:
            card = ctk.CTkFrame(self.rows_frame, fg_color=CARD_BG, border_width=1, border_color=BORDER_COLOR, corner_radius=8)
            card.pack(fill="x", pady=4, padx=2)
            
            def bind_card_events(widget):
                def on_enter(e, c=card):
                    c.configure(fg_color="#f8fafc", border_color="#cbd5e1")
                def on_leave(e, c=card):
                    c.configure(fg_color=CARD_BG, border_color=BORDER_COLOR)
                widget.bind("<Enter>", on_enter, add="+")
                widget.bind("<Leave>", on_leave, add="+")
                if self.double_click_callback:
                    widget.bind("<Double-1>", lambda e, d=row_data: self.double_click_callback(d))
                    
            bind_card_events(card)

            for i, col in enumerate(self.columns):
                weight = col.get("weight", 1)
                card.grid_columnconfigure(i, weight=int(weight*10), uniform="col")
                
                val = row_data.get(col["id"], "")
                
                cell_frame = ctk.CTkFrame(card, fg_color="transparent")
                cell_frame.grid(row=0, column=i, sticky="w", padx=10, pady=12)
                bind_card_events(cell_frame)

                if col.get("type") == "pill":
                    color = "#e2e8f0"
                    text_color = "#475569"
                    val_lower = str(val).lower()
                    if "completed" in val_lower or "done" in val_lower:
                        color = "#dcfce7"; text_color = "#166534"
                    elif "delayed" in val_lower or "overdue" in val_lower:
                        color = "#fee2e2"; text_color = "#991b1b"
                    elif "pending" in val_lower or "in progress" in val_lower or "active" in val_lower:
                        color = "#dbeafe"; text_color = "#1e40af"
                    elif "high" in val_lower or "urgent" in val_lower or "mrp" in val_lower:
                        color = "#fef08a"; text_color = "#854d0e"
                    elif "rfq" in val_lower:
                        color = "#f3e8ff"; text_color = "#7e22ce"
                        
                    pill = ctk.CTkLabel(cell_frame, text=str(val).upper()[:15], font=("Inter", 10, "bold"),
                                        fg_color=color, text_color=text_color, corner_radius=4, padx=8, pady=2)
                    pill.pack(anchor="w")
                    bind_card_events(pill)
                
                elif col.get("type") == "progress":
                    prog_val = float(val) if val else 0.0
                    prog_frame = ctk.CTkFrame(cell_frame, fg_color="transparent")
                    prog_frame.pack(anchor="w", fill="x", expand=True)
                    bind_card_events(prog_frame)
                    
                    bar = ctk.CTkProgressBar(prog_frame, width=80, height=8, corner_radius=4, progress_color=ACCENT_COLOR, fg_color=BORDER_COLOR)
                    bar.set(prog_val / 100.0)
                    bar.pack(side="left")
                    bind_card_events(bar)
                    
                    pct = ctk.CTkLabel(prog_frame, text=f"{int(prog_val)}%", font=FONT_SMALL, text_color=TEXT_MUTED)
                    pct.pack(side="left", padx=(5, 0))
                    bind_card_events(pct)
                    
                elif col.get("type") == "action":
                    btn = ctk.CTkButton(cell_frame, text="→", font=("Inter", 16, "bold"), fg_color="transparent", 
                                        text_color=TEXT_MUTED, hover_color=BG_COLOR, width=30,
                                        command=lambda d=row_data: self.double_click_callback(d) if self.double_click_callback else None)
                    btn.pack(anchor="w")
                
                else:
                    text_val = str(val)
                    if len(text_val) > 40: text_val = text_val[:37] + "..."
                    lbl = ctk.CTkLabel(cell_frame, text=text_val, font=FONT_MAIN, text_color=TEXT_COLOR)
                    lbl.pack(anchor="w")
                    bind_card_events(lbl)

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.data = new_data
        self._load_data(self.data)



class FilterBar(ctk.CTkFrame):
    def __init__(self, master, filter_options: List[Dict[str, Any]], on_filter_change: Callable, **kwargs):
        super().__init__(master, fg_color=CARD_BG, border_width=1,
                         border_color=BORDER_COLOR, corner_radius=6, **kwargs)
        self.on_filter_change = on_filter_change
        self.filter_options = filter_options
        self.filter_vars = {}

        col = 0
        for opt in filter_options:
            lbl = ctk.CTkLabel(self, text=opt["label"], text_color=TEXT_MUTED, font=FONT_MAIN)
            lbl.grid(row=0, column=col, padx=(10, 5), pady=10, sticky="w")
            col += 1

            default_val = opt.get("default", "All" if opt["type"] == "dropdown" else "")
            var = ctk.StringVar(value=default_val)
            self.filter_vars[opt["id"]] = var

            if opt["type"] == "dropdown":
                cb = ctk.CTkComboBox(self, values=opt["values"], variable=var,
                                     command=lambda v, o_id=opt["id"]: self._trigger_filter(),
                                     fg_color=BG_COLOR, border_width=1, border_color=BORDER_COLOR,
                                     text_color=TEXT_COLOR, button_color=BG_COLOR,
                                     button_hover_color=BORDER_COLOR,
                                     width=opt.get("width", 140))
                cb.grid(row=0, column=col, padx=(0, 15), pady=10)
            elif opt["type"] == "search":
                entry = ctk.CTkEntry(self, textvariable=var, placeholder_text="Search...",
                                     fg_color=BG_COLOR, border_width=1, border_color=BORDER_COLOR,
                                     text_color=TEXT_COLOR, width=opt.get("width", 200))
                entry.grid(row=0, column=col, padx=(0, 15), pady=10)
                var.trace_add("write", lambda *args: self._trigger_filter())
            col += 1

        btn_clear = ctk.CTkButton(self, text="Clear Filters", command=self._clear_filters,
                                  fg_color="transparent", text_color=ACCENT_COLOR,
                                  hover_color=BG_COLOR, border_width=1, border_color=ACCENT_COLOR)
        btn_clear.grid(row=0, column=col, padx=10, pady=10)

    def _trigger_filter(self):
        filters = {k: v.get() for k, v in self.filter_vars.items()}
        self.on_filter_change(filters)

    def _clear_filters(self, trigger=True):
        for opt in self.filter_options:
            default_val = opt.get("default", "All" if opt["type"] == "dropdown" else "")
            if opt["id"] in self.filter_vars:
                # Temporarily unbind to prevent trace triggers on search box
                var = self.filter_vars[opt["id"]]
                var.set(default_val)
        if trigger:
            self._trigger_filter()

class TimelineTracker(ctk.CTkFrame):
    def __init__(self, master, departments_status: List[Dict[str, Any]], **kwargs):
        super().__init__(master, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER_COLOR, **kwargs)
        self.departments_status = departments_status
        
        lbl = ctk.CTkLabel(self, text="Department Bottlenecks Tracker", font=FONT_TITLE, text_color=TEXT_COLOR)
        lbl.pack(anchor="w", padx=20, pady=(16, 4))
        
        self.canvas_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.canvas_frame.pack(fill="both", expand=True, padx=20, pady=(8, 20))
        
        self.canvas = tk.Canvas(self.canvas_frame, bg=CARD_BG, highlightthickness=0, height=140)
        self.canvas.pack(fill="both", expand=True)
        
        # Load custom icons
        try:
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
            
            x_img = Image.open(os.path.join(assets_dir, 'x_icon.png')).resize((40, 40), Image.LANCZOS)
            tick_img = Image.open(os.path.join(assets_dir, 'tick_icon.png')).resize((40, 40), Image.LANCZOS)
            
            self.x_icon = ImageTk.PhotoImage(x_img)
            self.tick_icon = ImageTk.PhotoImage(tick_img)
        except Exception as e:
            print(f"Error loading custom icons: {e}")
            self.x_icon = None
            self.tick_icon = None

        self.canvas.bind("<Configure>", self._draw_timeline)
        
    def _draw_timeline(self, event=None):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 50 or height < 50:
            return
            
        n = len(self.departments_status)
        if n == 0:
            self.canvas.create_text(width/2, height/2, text="No Departments", fill=TEXT_MUTED, font=FONT_MAIN)
            return
            
        pad_x = 90
        usable_width = width - 2 * pad_x
        step = usable_width / (n - 1) if n > 1 else 0
        y = height / 2 - 18
        
        # Horizontal track line behind nodes
        if n > 1:
            self.canvas.create_line(pad_x, y, pad_x + usable_width, y, fill="#e2e8f0", width=6, capstyle="round")
            
        for i, dept in enumerate(self.departments_status):
            x = pad_x + i * step
            is_bottleneck = dept.get("status", "green") == "red"
            color = "#ef4444" if is_bottleneck else "#10b981"
            
            # Outer halo / badge circle
            r = 20
            
            if is_bottleneck and getattr(self, 'x_icon', None):
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="white", outline="")
                self.canvas.create_image(x, y, image=self.x_icon)
            elif not is_bottleneck and getattr(self, 'tick_icon', None):
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="white", outline="")
                self.canvas.create_image(x, y, image=self.tick_icon)
            else:
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")
                # White icon inside circle
                if is_bottleneck:
                    # X icon
                    self.canvas.create_line(x - 7, y - 7, x + 7, y + 7, fill="white", width=3, capstyle="round")
                    self.canvas.create_line(x - 7, y + 7, x + 7, y - 7, fill="white", width=3, capstyle="round")
                else:
                    # Checkmark icon
                    self.canvas.create_line(x - 6, y, x - 1, y + 6, fill="white", width=3, capstyle="round")
                    self.canvas.create_line(x - 1, y + 6, x + 8, y - 5, fill="white", width=3, capstyle="round")
                
            # Department name
            self.canvas.create_text(x, y + 34, text=dept.get("name", ""), fill=TEXT_COLOR, font=("Inter", 13, "bold"))
            
            # Subtitle / description
            desc = dept.get("desc", "")
            if desc:
                desc_color = "#dc2626" if is_bottleneck else "#16a34a"
                self.canvas.create_text(x, y + 54, text=desc, fill=desc_color, font=("Inter", 11))
