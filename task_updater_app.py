import customtkinter as ctk

# Monkey patch CTkButton to always use cursor="hand2" for hover effect
original_button_init = ctk.CTkButton.__init__
def new_button_init(self, *args, **kwargs):
    kwargs.setdefault('cursor', 'hand2')
    original_button_init(self, *args, **kwargs)
ctk.CTkButton.__init__ = new_button_init
import tkinter as tk
import json
import time
import os
import sys
import threading
from tkinter import messagebox
from PIL import Image
from config import COLORS, FONTS, DEPARTMENTS

# Adjust font sizes for task_updater_app
FONTS = {
    key: (val[0], int(val[1] * 1.25), *(v for v in val[2:] if v != "bold")) if isinstance(val, (tuple, list)) else val
    for key, val in FONTS.items()
}

COLORS = {
    "bg": "#F6F8FB",
    "card_bg": "#FFFFFF",
    "sidebar_bg": "#F9FAFC",
    "input_bg": "#FFFFFF",
    "accent": "#2563EB",
    "accent_hover": "#1d4ed8",
    "highlight": "#EF4444",
    "highlight_hover": "#dc2626",
    "text_main": "#172033",
    "text_dim": "#64748B",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "border": "#E2E8F0",
    "primary_navy": "#172B4D",
    "info": "#3B82F6"
}
from services.n8n_client import N8nClient
from services.supabase_client import SupabaseClient
from services.extension_store import (
    submit_extension_request,
    get_requests_for_employee,
)
from services.local_sync import record_task_update
from tkcalendar import DateEntry
from datetime import datetime
import traceback

# Resolve paths relative to exe directory when frozen
if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

def _setup_crash_proof_environment():
    """Catches unhandled errors in main and worker threads, logs to crash_log.txt without crashing."""
    crash_log_file = os.path.join(_APP_DIR, "crash_log.txt")

    def global_excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"Unhandled exception prevented:\n{err_msg}")
        try:
            with open(crash_log_file, "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] UNHANDLED ERROR:\n{err_msg}\n")
        except Exception:
            pass

    sys.excepthook = global_excepthook

    if hasattr(threading, 'excepthook'):
        def thread_excepthook(args):
            err_msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
            print(f"Thread error in {args.thread.name} prevented:\n{err_msg}")
            try:
                with open(crash_log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] THREAD ERROR ({args.thread.name}):\n{err_msg}\n")
            except Exception:
                pass
        threading.excepthook = thread_excepthook

_setup_crash_proof_environment()

def _resolve_resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(p):
            return p
    if getattr(sys, 'frozen', False):
        p = os.path.join(os.path.dirname(sys.executable), filename)
        if os.path.exists(p):
            return p
    candidates = [
        os.path.join(_APP_DIR, filename),
        os.path.join(os.getcwd(), filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return filename

CACHE_FILE = os.path.join(_APP_DIR, "recent_task_updates.json")
_USER_ICO_PATH = _resolve_resource_path("user.ico")

# ── Helpers ──────────────────────────────────────────────────────────────

def format_date(date_str):
    if not date_str or date_str in ("N/A", "None", ""):
        return "N/A"
    s = str(date_str).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%d %b %Y")
        except ValueError:
            pass
    return s


def _parse_deadline(date_str):
    """Try to parse a deadline string into a date object.  Returns None on failure."""
    if not date_str or date_str in ("N/A", "None", ""):
        return None
    s = str(date_str).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def load_recent_updates():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                current_time = time.time()
                return {k: v for k, v in data.items() if current_time - v.get("timestamp", 0) < 600}
    except Exception:
        pass
    return {}


def save_recent_updates(updates_dict):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(updates_dict, f)
    except Exception:
        pass


def _hex_to_rgb(hex_str):
    hex_str = str(hex_str).lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(c * 2 for c in hex_str)
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    r = max(0, min(255, int(round(rgb[0]))))
    g = max(0, min(255, int(round(rgb[1]))))
    b = max(0, min(255, int(round(rgb[2]))))
    return f"#{r:02x}{g:02x}{b:02x}"


def _interpolate_color(c1, c2, factor):
    try:
        rgb1 = _hex_to_rgb(c1)
        rgb2 = _hex_to_rgb(c2)
        factor = max(0.0, min(1.0, float(factor)))
        return _rgb_to_hex(tuple(rgb1[i] + (rgb2[i] - rgb1[i]) * factor for i in range(3)))
    except Exception:
        return c2


class ModernComboBox(ctk.CTkComboBox):
    """Clean, light-themed combobox with no text editing cursor and seamless white dropdown styling."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("fg_color", "#FFFFFF")
        kwargs.setdefault("button_color", "#FFFFFF")
        kwargs.setdefault("button_hover_color", "#F8FAFC")
        kwargs.setdefault("border_color", COLORS["border"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("dropdown_fg_color", "#FFFFFF")
        kwargs.setdefault("dropdown_hover_color", "#F1F5F9")
        kwargs.setdefault("dropdown_text_color", COLORS["text_main"])
        kwargs.setdefault("text_color", COLORS["text_main"])
        super().__init__(*args, **kwargs)
        self.configure(state="readonly")

        try:
            self._canvas.itemconfig("border_parts_right",
                                    outline=self._apply_appearance_mode(self._border_color),
                                    fill=self._apply_appearance_mode(self._border_color))
        except Exception:
            pass

        try:
            self._entry.configure(cursor="hand2", insertwidth=0, selectbackground="#FFFFFF",
                                  selectforeground=COLORS["text_main"], takefocus=0)
            self._entry.bind("<Button-1>", self._on_entry_click)
        except Exception:
            pass

    def _on_entry_click(self, event=None):
        if self._dropdown_menu.is_open():
            self._dropdown_menu.close()
            self._close_on_next_click = False
        elif self._state != tk.DISABLED and len(self._values) > 0:
            self._open_dropdown_menu()
        return "break"

    def _draw(self, no_color_updates=False):
        super()._draw(no_color_updates)
        try:
            self._canvas.itemconfig("border_parts_right",
                                    outline=self._apply_appearance_mode(self._border_color),
                                    fill=self._apply_appearance_mode(self._border_color))
        except Exception:
            pass

    def _on_enter(self, event=0):
        super()._on_enter(event)
        self._close_on_next_click = self._dropdown_menu.is_open()
        if self._hover is True and len(self._values) > 0:
            self._canvas.configure(cursor="hand2")
            self._canvas.itemconfig("inner_parts_right",
                                    outline=self._apply_appearance_mode(self._button_hover_color),
                                    fill=self._apply_appearance_mode(self._button_hover_color))

    def _on_leave(self, event=0):
        super()._on_leave(event)
        self._canvas.configure(cursor="arrow")
        self._canvas.itemconfig("inner_parts_right",
                                outline=self._apply_appearance_mode(self._button_color),
                                fill=self._apply_appearance_mode(self._button_color))
        self._canvas.itemconfig("border_parts_right",
                                outline=self._apply_appearance_mode(self._border_color),
                                fill=self._apply_appearance_mode(self._border_color))


# ═════════════════════════════════════════════════════════════════════════
# Main Application
# ═════════════════════════════════════════════════════════════════════════

def fade_in(window, target_alpha=1.0, current=0.0, step=0.08, delay=15):
    try:
        if current < target_alpha:
            current += step
            if current > target_alpha:
                current = target_alpha
            window.attributes("-alpha", current)
            window.after(delay, fade_in, window, target_alpha, current, step, delay)
        else:
            window.attributes("-alpha", target_alpha)
    except Exception:
        pass

class TaskUpdaterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.attributes("-alpha", 0.0)
        ctk.set_appearance_mode("Light")
        self.title("Balbird TO - Employee Portal")
        self.geometry("1050x900")
        self.configure(fg_color=COLORS["bg"])
        self.after(0, lambda: self.state("zoomed"))

        try:
            if os.path.exists(_USER_ICO_PATH):
                self.iconbitmap(_USER_ICO_PATH)
        except Exception:
            pass

        self.n8n_client = N8nClient()
        self.sheets_client = SupabaseClient()

        self.departments = DEPARTMENTS
        self.current_tasks = []       # all tasks fetched for the employee
        self.status_vars = {}         # maps task_id → tk.StringVar
        self.modified_task_info = {}  # maps task_id → dict of modifications

        self.current_dept = None
        self.current_user = None

        # Sorting / filtering / search state
        self._sort_param = "deadline"     # "deadline" | "priority" | "assigned" | "status"
        self._sort_dir = "asc"            # "asc" | "desc"
        self._filter_status = "Active"    # Active | All | Completed | Overdue | Delayed | High Priority
        self.search_var = ctk.StringVar()

        # Differential & seamless refresh state
        self._task_rows = {}                # maps task_id -> row info dict
        self._ext_rows = {}                 # maps ext_key -> ext row info dict
        self._known_task_ids = set()        # set of seen task_id strings
        self._is_initial_load = True        # True until first batch of tasks renders
        self._user_dropdown_selections = {} # maps task_id -> user-selected status
        self._is_fetching = False           # avoids overlapping background fetches
        self._pending_refresh = False       # queues refresh if fetch was busy

        self.setup_login_ui()
        fade_in(self)

    # ═════════════════════════════════════════════════════════════════════
    # Login Screen
    # ═════════════════════════════════════════════════════════════════════

    def setup_login_ui(self):
        self.login_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.login_frame.pack(fill="both", expand=True, padx=20, pady=20)

        card = ctk.CTkFrame(self.login_frame, fg_color=COLORS["card_bg"], corner_radius=12,
                            border_width=1, border_color=COLORS["border"])
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Portal Icon Branding
        self._login_icon_img = None
        if os.path.exists(_USER_ICO_PATH):
            try:
                pil_icon = Image.open(_USER_ICO_PATH)
                self._login_icon_img = ctk.CTkImage(light_image=pil_icon, dark_image=pil_icon, size=(52, 52))
                lbl_icon = ctk.CTkLabel(card, text="", image=self._login_icon_img)
                lbl_icon.pack(pady=(35, 10))
            except Exception:
                pass

        top_pad = 0 if self._login_icon_img else 35
        ctk.CTkLabel(card, text="Balbird TO", font=(FONTS["header"][0], 24, "bold"),
                     text_color=COLORS["text_main"]).pack(pady=(top_pad, 2), padx=50)
        ctk.CTkLabel(card, text="Employee Portal", font=(FONTS["body"][0], 13, "bold"),
                     text_color=COLORS["accent"]).pack(pady=(0, 6), padx=50)
        ctk.CTkLabel(card, text="Please select your department and name to continue",
                     font=FONTS["small"], text_color=COLORS["text_dim"]).pack(pady=(0, 24), padx=50)

        self.login_combo_dept = ModernComboBox(
            card, values=list(self.departments.keys()),
            command=self.on_login_dept_select, width=400, height=48,
            font=FONTS["body"], dropdown_font=FONTS["body"], corner_radius=8)
        self.login_combo_dept.pack(pady=(0, 15), padx=50)

        self.login_combo_person = ModernComboBox(
            card, values=[], width=400, height=48,
            font=FONTS["body"], dropdown_font=FONTS["body"], corner_radius=8)
        self.login_combo_person.pack(pady=(0, 25), padx=50)

        ctk.CTkButton(card, text="Continue", font=FONTS["body"],
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      command=self.do_login, width=400, height=48).pack(pady=(0, 30), padx=50)

        if list(self.departments.keys()):
            self.login_combo_dept.set(list(self.departments.keys())[0])
            self.on_login_dept_select(self.login_combo_dept.get())

    def on_login_dept_select(self, dept):
        people = self.departments.get(dept, [])
        self.login_combo_person.configure(values=people)
        if people:
            self.login_combo_person.set(people[0])
        else:
            self.login_combo_person.set("")

    def do_login(self):
        dept = self.login_combo_dept.get()
        person = self.login_combo_person.get()
        if not dept or not person:
            messagebox.showwarning("Missing Info", "Please select both department and name.")
            return
        self.current_dept = dept
        self.current_user = person
        self.login_frame.destroy()
        self.setup_main_ui()
        self._start_auto_refresh()

    # ═════════════════════════════════════════════════════════════════════
    # Main Dashboard UI
    # ═════════════════════════════════════════════════════════════════════

    def setup_main_ui(self):
        # ── Header bar ──
        header_bar = ctk.CTkFrame(self, fg_color=COLORS["card_bg"], corner_radius=0, height=84,
                                  border_width=1, border_color=COLORS["border"])
        header_bar.pack(fill="x")
        header_bar.pack_propagate(False)

        left_header = ctk.CTkFrame(header_bar, fg_color="transparent")
        left_header.pack(side="left", padx=24, pady=8)
        
        # Portal Icon Branding
        self._header_icon_img = None
        if os.path.exists(_USER_ICO_PATH):
            try:
                pil_icon = Image.open(_USER_ICO_PATH)
                self._header_icon_img = ctk.CTkImage(light_image=pil_icon, dark_image=pil_icon, size=(42, 42))
            except Exception:
                pass

        if self._header_icon_img:
            ctk.CTkLabel(left_header, text="", image=self._header_icon_img).pack(side="left", padx=(0, 14))
        else:
            ctk.CTkLabel(left_header, text="👤", font=("Segoe UI", 28)).pack(side="left", padx=(0, 14))
        
        # Brand & User Info Container
        brand_container = ctk.CTkFrame(left_header, fg_color="transparent")
        brand_container.pack(side="left")

        title_line = ctk.CTkFrame(brand_container, fg_color="transparent")
        title_line.pack(anchor="w")
        ctk.CTkLabel(title_line, text="Balbird TO", font=("Segoe UI", 16, "bold"),
                     text_color=COLORS["text_main"]).pack(side="left")
        ctk.CTkLabel(title_line, text=" • Employee Portal", font=("Segoe UI", 11, "bold"),
                     text_color=COLORS["accent"]).pack(side="left", padx=(4, 0))

        sub_line = ctk.CTkFrame(brand_container, fg_color="transparent")
        sub_line.pack(anchor="w", pady=(1, 0))
        ctk.CTkLabel(sub_line, text=self.current_user, font=FONTS["body"],
                     text_color=COLORS["text_main"]).pack(side="left")
        ctk.CTkLabel(sub_line, text=f"({self.current_dept})", font=FONTS["small"],
                     text_color=COLORS["text_dim"]).pack(side="left", padx=(6, 0))

        btn_frame = ctk.CTkFrame(header_bar, fg_color="transparent")
        btn_frame.pack(side="right", padx=24, pady=8)

        ctk.CTkButton(btn_frame, text="＋ Add Task", width=110, height=36,
                      font=FONTS["body"], fg_color=COLORS["accent"], text_color="#FFFFFF", corner_radius=6,
                      hover_color=COLORS["accent_hover"],
                      command=self._show_add_task_dialog).pack(side="left", padx=(0, 12))

        self.btn_refresh = ctk.CTkButton(btn_frame, text="↻ Refresh", width=90, height=36,
                                         font=FONTS["body"], fg_color="#FFFFFF", text_color=COLORS["primary_navy"], corner_radius=6,
                                         border_width=1, border_color=COLORS["border"], hover_color=COLORS["bg"],
                                         command=self._full_refresh)
        self.btn_refresh.pack(side="left")

        # ── Main Static Container (Fills window below header bar) ──
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=24, pady=(16, 20))

        self._init_dashboard_containers()
        self._trigger_fetch(is_background=False)

    def _init_dashboard_containers(self):
        """Builds static KPI bar and independent scrollable containers for tasks and extensions."""
        # 1. KPI Outer Frame (Static at the top — always visible!)
        self.kpi_outer = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.kpi_outer.pack(fill="x", pady=(0, 14))
        self.kpi_labels = {}

        cards_data = [
            ("total",              "Total Tasks",      "-", "#F1F5F9", "#0F172A"),
            ("active",             "Active",           "-", "#EFF6FF", "#1E3A8A"),
            ("completed",          "Completed",        "-", "#ECFDF5", "#065F46"),
            ("overdue",            "Overdue",          "-", "#FEF2F2", "#991B1B"),
            ("due_today",          "Due Today",        "-", "#FFFBEB", "#92400E"),
            ("due_this_week",      "Due This Week",    "-", "#F8FAFC", "#334155"),
            ("high_priority",      "High / Urgent",    "-", "#FEF2F2", "#991B1B"),
            ("pending_extensions", "Pending Ext.",     "-", "#F5F3FF", "#4C1D95"),
        ]

        for row_idx in range(2):
            row_frame = ctk.CTkFrame(self.kpi_outer, fg_color="transparent")
            row_frame.pack(fill="x", pady=3)
            for col_idx in range(4):
                row_frame.grid_columnconfigure(col_idx, weight=1, uniform="kpi_col")

            for col_idx in range(4):
                i = row_idx * 4 + col_idx
                if i >= len(cards_data):
                    break
                key, label, val_default, bg_color, txt_color = cards_data[i]
                card = ctk.CTkFrame(row_frame, fg_color=bg_color,
                                    corner_radius=10, border_width=1, border_color=COLORS["border"])
                card.grid(row=0, column=col_idx, sticky="nsew", padx=6, pady=2)

                lbl_val = ctk.CTkLabel(card, text=val_default, font=(FONTS["header"][0], 22, "bold"),
                                       text_color=txt_color, fg_color="transparent")
                lbl_val.pack(anchor="w", padx=16, pady=(10, 0))
                self.kpi_labels[key] = lbl_val

                ctk.CTkLabel(card, text=label, font=FONTS["small"],
                             text_color=txt_color, fg_color="transparent").pack(anchor="w", padx=16, pady=(2, 10))

        # 2. Main Two-Column Frame (Fills all remaining vertical height)
        columns_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        columns_frame.pack(fill="both", expand=True)
        columns_frame.grid_columnconfigure(0, weight=7)
        columns_frame.grid_columnconfigure(1, weight=3)
        columns_frame.grid_rowconfigure(0, weight=1)

        left_col = ctk.CTkFrame(columns_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        right_col = ctk.CTkFrame(columns_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # ── Left Column: My Tasks Section ──
        tasks_section = ctk.CTkFrame(left_col, fg_color=COLORS["card_bg"],
                                     corner_radius=12, border_width=1, border_color=COLORS["border"])
        tasks_section.pack(fill="both", expand=True)

        hdr_left = ctk.CTkFrame(tasks_section, fg_color="transparent")
        hdr_left.pack(fill="x", padx=20, pady=(16, 10))

        title_frame = ctk.CTkFrame(hdr_left, fg_color="transparent")
        title_frame.pack(side="left")
        ctk.CTkLabel(title_frame, text="My Tasks", font=("Segoe UI", 18, "bold"), text_color=COLORS["text_main"]).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Tasks assigned to you and their current status",
                     font=FONTS["small"], text_color=COLORS["text_dim"]).pack(anchor="w", pady=(1, 0))

        toolbar = ctk.CTkFrame(hdr_left, fg_color="transparent")
        toolbar.pack(side="right", pady=2)

        # Search Entry with instant clear button
        search_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        search_box.pack(side="left", padx=(0, 10))

        self.search_entry = ctk.CTkEntry(
            search_box, textvariable=self.search_var, placeholder_text="🔍 Search tasks...",
            width=210, height=34, font=FONTS["small"], fg_color="#FFFFFF",
            border_width=1, border_color=COLORS["border"], corner_radius=6,
            text_color=COLORS["text_main"]
        )
        self.search_entry.pack(side="left")

        self.btn_clear_search = ctk.CTkButton(
            search_box, text="✕", width=28, height=34, font=("Segoe UI", 11),
            fg_color="#FFFFFF", hover_color=COLORS["bg"], text_color=COLORS["text_dim"],
            border_width=1, border_color=COLORS["border"], corner_radius=6,
            command=lambda: [self.search_var.set(""), self.search_entry.focus_set()]
        )
        self.btn_clear_search.pack(side="left", padx=(4, 0))

        self.search_entry.bind("<Escape>", lambda _: [self.search_var.set(""), self.search_entry.focus_set()])
        self.search_var.trace_add("write", lambda *_: self._on_sort_filter_change())

        self.filter_combo = ModernComboBox(
            toolbar, values=["Active", "All", "Completed", "Overdue", "Delayed", "High Priority"],
            width=150, height=34, font=FONTS["small"], dropdown_font=FONTS["small"], corner_radius=6,
            command=lambda _: self._on_sort_filter_change())
        self.filter_combo.set(self._filter_status)
        self.filter_combo.pack(side="left")

        # ── Parameter Sort Bar (Click once -> asc, click again -> desc with reversed arrow!) ──
        self.sort_bar = ctk.CTkFrame(tasks_section, fg_color="transparent")
        self.sort_bar.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(self.sort_bar, text="Sort by:", font=FONTS["small"],
                     text_color=COLORS["text_dim"]).pack(side="left", padx=(0, 10))

        self.sort_buttons = {}
        sort_params = [
            ("deadline", "Deadline"),
            ("priority", "Priority"),
            ("assigned", "Assigned Date"),
            ("status",   "Status"),
        ]

        for param_key, param_label in sort_params:
            btn = ctk.CTkButton(
                self.sort_bar, text=f"{param_label} ↕", width=110, height=30,
                font=FONTS["small"], fg_color="#FFFFFF", hover_color="#F1F5F9",
                text_color=COLORS["text_dim"], border_width=1, border_color=COLORS["border"],
                corner_radius=6, command=lambda p=param_key: self._on_sort_param_click(p)
            )
            btn.pack(side="left", padx=(0, 8))
            self.sort_buttons[param_key] = (btn, param_label)

        self._update_sort_buttons_ui()

        # Individual Scrollable Container for Tasks (Only this window scrolls!)
        self.tasks_container = ctk.CTkScrollableFrame(tasks_section, fg_color="transparent")
        self.tasks_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.tasks_container.grid_columnconfigure(0, weight=1)
        self.body_scroll = self.tasks_container  # backwards-compatibility alias

        self.tasks_loading_lbl = ctk.CTkLabel(self.tasks_container, text="Loading your tasks, please wait...",
                                              font=FONTS["body"], text_color=COLORS["text_dim"])
        self.tasks_loading_lbl.pack(pady=30)

        self.empty_tasks_frame = ctk.CTkFrame(self.tasks_container, fg_color="transparent")
        self.lbl_empty_title = ctk.CTkLabel(self.empty_tasks_frame, text="No active tasks", font=FONTS["subheader"], text_color=COLORS["text_main"])
        self.lbl_empty_title.pack()
        self.lbl_empty_desc = ctk.CTkLabel(self.empty_tasks_frame, text="You currently have no tasks matching this filter.", font=FONTS["body"], text_color=COLORS["text_dim"])
        self.lbl_empty_desc.pack(pady=(5, 15))
        ctk.CTkButton(self.empty_tasks_frame, text="Clear Filters & Search", font=FONTS["body"], fg_color="transparent",
                      border_width=1, border_color=COLORS["border"], text_color=COLORS["text_main"], hover_color=COLORS["bg"],
                      command=lambda: [self.filter_combo.set("All"), self.search_var.set(""), self._on_sort_filter_change()]).pack()

        # ── Right Column: Extension Requests Section ──
        ext_section = ctk.CTkFrame(right_col, fg_color=COLORS["card_bg"],
                                   corner_radius=12, border_width=1, border_color=COLORS["border"])
        ext_section.pack(fill="both", expand=True)

        hdr_right = ctk.CTkFrame(ext_section, fg_color="transparent")
        hdr_right.pack(fill="x", padx=20, pady=(16, 10))

        title_r_frame = ctk.CTkFrame(hdr_right, fg_color="transparent")
        title_r_frame.pack(side="left")
        ctk.CTkLabel(title_r_frame, text="My Extension Requests", font=("Segoe UI", 18, "bold"), text_color=COLORS["text_main"]).pack(anchor="w")
        ctk.CTkLabel(title_r_frame, text="Track your deadline change requests",
                     font=FONTS["small"], text_color=COLORS["text_dim"]).pack(anchor="w", pady=(1, 0))

        self.btn_ext_refresh = ctk.CTkButton(hdr_right, text="↻", width=34, font=FONTS["small"], corner_radius=6,
                                             fg_color="transparent", border_width=1, border_color=COLORS["border"],
                                             text_color=COLORS["text_main"], hover_color=COLORS["bg"],
                                             height=34, command=self._full_refresh)
        self.btn_ext_refresh.pack(side="right")

        # Individual Scrollable Container for Extension Requests (Only this window scrolls!)
        self.ext_container = ctk.CTkScrollableFrame(ext_section, fg_color="transparent")
        self.ext_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.ext_loading_lbl = ctk.CTkLabel(self.ext_container, text="Loading requests...", font=FONTS["body"], text_color=COLORS["text_dim"])
        self.ext_loading_lbl.pack(pady=30)

        self.empty_ext_frame = ctk.CTkFrame(self.ext_container, fg_color="transparent")
        ctk.CTkLabel(self.empty_ext_frame, text="No extension requests yet.", font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=40)

    def _trigger_fetch(self, is_background=False):
        """Asynchronously fetches data and applies it in-place without resetting scroll or widget states."""
        if getattr(self, '_is_fetching', False):
            self._pending_refresh = True
            return

        self._is_fetching = True
        self._current_render_id = getattr(self, '_current_render_id', 0) + 1
        current_id = self._current_render_id

        if not is_background:
            if hasattr(self, "btn_refresh"):
                try:
                    self.btn_refresh.configure(text="↻ Syncing...", state="disabled")
                except Exception:
                    pass

        def fetch_data_thread():
            try:
                self._fetch_tasks_data()
                ext_requests = get_requests_for_employee(self.current_user or "")
            except Exception as e:
                print(f"Error fetching data: {e}")
                ext_requests = []

            def apply_if_current():
                try:
                    self._is_fetching = False
                    if hasattr(self, "btn_refresh"):
                        try:
                            self.btn_refresh.configure(text="↻ Refresh", state="normal")
                        except Exception:
                            pass
                    if hasattr(self, "btn_ext_refresh"):
                        try:
                            self.btn_ext_refresh.configure(state="normal")
                        except Exception:
                            pass

                    if self._current_render_id == current_id:
                        self._apply_dashboard_data(ext_requests)

                    if getattr(self, '_pending_refresh', False):
                        self._pending_refresh = False
                        self._trigger_fetch(is_background=True)
                except Exception as e:
                    print(f"Error applying dashboard updates: {e}")

            self.after(0, apply_if_current)

        threading.Thread(target=fetch_data_thread, daemon=True).start()

    def _build_dashboard_content(self, is_background=False):
        """Backwards compatibility shim for _trigger_fetch."""
        self._trigger_fetch(is_background=is_background)

    def _apply_dashboard_data(self, ext_requests):
        """Calculates derived metrics and updates KPI, tasks, and extensions in place."""
        if hasattr(self, "tasks_loading_lbl") and self.tasks_loading_lbl.winfo_exists():
            self.tasks_loading_lbl.pack_forget()
        if hasattr(self, "ext_loading_lbl") and self.ext_loading_lbl.winfo_exists():
            self.ext_loading_lbl.pack_forget()

        today = datetime.now().date()
        all_tasks = self.current_tasks

        self._approved_ext = {}
        for req in ext_requests:
            if req.get("status") == "Approved":
                self._approved_ext[req["task_id"]] = req.get("manager_deadline") or req.get("requested_deadline")

        for t in all_tasks:
            eff_dl = self._approved_ext.get(t.task_id, t.deadline)
            t._effective_deadline = eff_dl
            t._effective_deadline_date = _parse_deadline(eff_dl)
            t._is_extended = t.task_id in self._approved_ext

        active_tasks = [t for t in all_tasks if t.status.lower() not in ("completed", "done")]
        completed_tasks = [t for t in all_tasks if t.status.lower() in ("completed", "done")]
        overdue_tasks = [t for t in active_tasks if t._effective_deadline_date and t._effective_deadline_date < today]
        due_today_tasks = [t for t in active_tasks if t._effective_deadline_date and t._effective_deadline_date == today]
        due_this_week = [t for t in active_tasks
                         if t._effective_deadline_date
                         and today <= t._effective_deadline_date
                         and (t._effective_deadline_date - today).days <= 7]
        high_priority = [t for t in active_tasks if t.priority.lower() in ("high", "urgent")]
        pending_ext = [r for r in ext_requests if r["status"] == "Pending"]

        # 1. Update KPI numbers in-place
        self._update_kpi_section(
            total=len(all_tasks),
            active=len(active_tasks),
            completed=len(completed_tasks),
            overdue=len(overdue_tasks),
            due_today=len(due_today_tasks),
            due_this_week=len(due_this_week),
            high_priority=len(high_priority),
            pending_extensions=len(pending_ext),
        )

        # 2. Update task cards in-place with diffing & smooth entrance animation
        self._update_tasks_display(all_tasks, today)

        # 3. Update extension request cards in-place
        self._update_extension_display(ext_requests)

    def _update_kpi_section(self, **kpis):
        """Updates numeric labels in the KPI section without rebuilding frames."""
        mapping = {
            "total": str(kpis["total"]),
            "active": str(kpis["active"]),
            "completed": str(kpis["completed"]),
            "overdue": str(kpis["overdue"]),
            "due_today": str(kpis["due_today"]),
            "due_this_week": str(kpis["due_this_week"]),
            "high_priority": str(kpis["high_priority"]),
            "pending_extensions": str(kpis["pending_extensions"]),
        }
        for key, val in mapping.items():
            lbl = self.kpi_labels.get(key)
            if lbl and lbl.winfo_exists() and lbl.cget("text") != val:
                lbl.configure(text=val)

    def _on_sort_param_click(self, param):
        """Click once -> ascending (↑). Click same again -> descending (↓) with reversed arrow."""
        if self._sort_param == param:
            self._sort_dir = "desc" if self._sort_dir == "asc" else "asc"
        else:
            self._sort_param = param
            self._sort_dir = "asc"

        self._update_sort_buttons_ui()
        self._on_sort_filter_change()

    def _update_sort_buttons_ui(self):
        """Updates text and visual highlight on sort buttons to reflect active param and arrow direction."""
        if not hasattr(self, "sort_buttons"):
            return
        for param_key, (btn, param_label) in self.sort_buttons.items():
            try:
                if not btn.winfo_exists():
                    continue
                if param_key == self._sort_param:
                    arrow = "↑" if self._sort_dir == "asc" else "↓"
                    btn.configure(
                        text=f"{param_label} {arrow}",
                        fg_color=COLORS["accent"],
                        text_color="#FFFFFF",
                        hover_color=COLORS["accent_hover"],
                        border_color=COLORS["accent"],
                        font=(FONTS["small"][0], FONTS["small"][1], "bold")
                    )
                else:
                    btn.configure(
                        text=f"{param_label} ↕",
                        fg_color="#FFFFFF",
                        text_color=COLORS["text_dim"],
                        hover_color="#F1F5F9",
                        border_color=COLORS["border"],
                        font=FONTS["small"]
                    )
            except Exception:
                pass

    def _on_sort_filter_change(self):
        """Called when employee changes filter, search query, or sort parameters."""
        if hasattr(self, "filter_combo"):
            self._filter_status = self.filter_combo.get()
        today = datetime.now().date()
        self._update_tasks_display(self.current_tasks, today)

    def _update_tasks_display(self, all_tasks, today):
        """Seamlessly updates the task list in place, preserving scroll position and active dropdowns."""
        # 1. Capture current scroll position to maintain it exactly
        current_scroll = None
        try:
            current_scroll = self.tasks_container._parent_canvas.yview()[0]
        except Exception:
            pass

        # 2. Filter tasks by status dropdown
        filt = self.filter_combo.get() if hasattr(self, "filter_combo") else self._filter_status
        if filt == "Active":
            tasks = [t for t in all_tasks if t.status.lower() not in ("completed", "done")]
        elif filt == "Completed":
            tasks = [t for t in all_tasks if t.status.lower() in ("completed", "done")]
        elif filt == "Overdue":
            tasks = [t for t in all_tasks
                     if t.status.lower() not in ("completed", "done")
                     and t._effective_deadline_date and t._effective_deadline_date < today]
        elif filt == "Delayed":
            tasks = [t for t in all_tasks if t.status.lower() == "delayed"]
        elif filt == "High Priority":
            tasks = [t for t in all_tasks
                     if t.status.lower() not in ("completed", "done")
                     and t.priority.lower() in ("high", "urgent")]
        else:
            tasks = list(all_tasks)

        # 3. Filter tasks by search query (multi-token search across ID, description, priority, dates, checklist)
        search_query = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        if search_query:
            tokens = search_query.split()
            filtered_by_search = []
            for t in tasks:
                t_id = str(getattr(t, "task_id", "") or "")
                short_id = t_id[-4:] if len(t_id) >= 4 else t_id
                desc = str(getattr(t, "description", "") or getattr(t, "task", "") or "")
                prio = str(getattr(t, "priority", "") or "")
                stat = str(getattr(t, "status", "") or "")
                assigned_d = str(getattr(t, "date", "") or "")
                eff_dl = str(getattr(t, "_effective_deadline", "") or getattr(t, "deadline", "") or "")
                eff_dl_fmt = format_date(eff_dl) if eff_dl else ""

                chk_items = []
                chk = getattr(t, "checklist", None)
                if isinstance(chk, list):
                    for item in chk:
                        if isinstance(item, dict):
                            chk_items.append(str(item.get("item", "")))
                        else:
                            chk_items.append(str(item))
                chk_text = " ".join(chk_items)

                searchable = f"{t_id} {short_id} {desc} {prio} {stat} {assigned_d} {eff_dl} {eff_dl_fmt} {chk_text}".lower()
                if all(tok in searchable for tok in tokens):
                    filtered_by_search.append(t)
            tasks = filtered_by_search

        # 4. Sort tasks according to active parameter & direction (asc / desc)
        far_future = datetime(2099, 12, 31).date()
        is_desc = (self._sort_dir == "desc")

        if self._sort_param == "deadline":
            if not is_desc:
                tasks.sort(key=lambda t: (t._effective_deadline_date is None, t._effective_deadline_date or far_future))
            else:
                tasks.sort(key=lambda t: (t._effective_deadline_date is None, -(t._effective_deadline_date.toordinal() if t._effective_deadline_date else 0)))
        elif self._sort_param == "priority":
            prio_order = {"urgent": 0, "high": 1, "medium": 2, "normal": 2, "low": 3}
            tasks.sort(key=lambda t: prio_order.get(str(t.priority).strip().lower(), 9), reverse=is_desc)
        elif self._sort_param == "assigned":
            if not is_desc:
                tasks.sort(key=lambda t: (_parse_deadline(t.date) is None, _parse_deadline(t.date) or far_future))
            else:
                tasks.sort(key=lambda t: (_parse_deadline(t.date) is None, -(_parse_deadline(t.date).toordinal() if _parse_deadline(t.date) else 0)))
        elif self._sort_param == "status":
            status_order = {"delayed": 0, "overdue": 1, "active": 2, "in progress": 3, "pending": 4, "completed": 5, "done": 6}
            tasks.sort(key=lambda t: status_order.get(str(t.status).strip().lower(), 9), reverse=is_desc)

        # 5. Handle empty state
        if not tasks:
            for info in self._task_rows.values():
                info["row_widget"].grid_remove()
            if hasattr(self, "empty_tasks_frame"):
                if search_query:
                    if hasattr(self, "lbl_empty_title"):
                        self.lbl_empty_title.configure(text="No matching tasks found")
                    if hasattr(self, "lbl_empty_desc"):
                        self.lbl_empty_desc.configure(text=f"No tasks match your search \"{self.search_var.get().strip()}\".")
                else:
                    if hasattr(self, "lbl_empty_title"):
                        self.lbl_empty_title.configure(text=f"No {filt.lower()} tasks")
                    if hasattr(self, "lbl_empty_desc"):
                        self.lbl_empty_desc.configure(text=f"You currently have no tasks matching the \"{filt}\" filter.")
                self.empty_tasks_frame.pack(pady=40)
            return

        if hasattr(self, "empty_tasks_frame"):
            self.empty_tasks_frame.pack_forget()

        # 5. Differential row updates
        target_ids = [t.task_id for t in tasks]
        target_ids_set = set(target_ids)
        existing_ids = set(self._task_rows.keys())

        # Hide rows that don't match the active filter
        for t_id in existing_ids:
            if t_id not in target_ids_set:
                self._task_rows[t_id]["row_widget"].grid_remove()

        # Detect if employee currently has any dropdown actively opened
        user_interacting = False
        for info in self._task_rows.values():
            combo = info.get("status_combo")
            if combo and hasattr(combo, "_dropdown_menu") and combo._dropdown_menu.is_open():
                user_interacting = True
                break

        # Render or update each task in sorted order
        for idx, task in enumerate(tasks):
            t_id = task.task_id
            if t_id in self._task_rows:
                info = self._task_rows[t_id]
                self._update_existing_task_row(info, task, today, user_interacting)
            else:
                # Brand new task
                is_brand_new = (not self._is_initial_load) and (t_id not in self._known_task_ids)
                info = self._create_task_row(task, today, is_brand_new=is_brand_new)
                self._task_rows[t_id] = info

            self._known_task_ids.add(t_id)

            # Re-grid at the sorted position
            info["row_widget"].grid(row=idx, column=0, sticky="ew", pady=4)

        if self._is_initial_load:
            self._is_initial_load = False

        # 6. Restore scroll position seamlessly
        if current_scroll is not None:
            try:
                self.after_idle(lambda: self.tasks_container._parent_canvas.yview_moveto(current_scroll))
            except Exception:
                pass

    def _update_existing_task_row(self, info, task, today, user_interacting):
        """Updates text and badges on an existing task card in-place while preserving combobox selections."""
        old_task = info["task"]
        info["task"] = task

        # Format deadlines
        eff_dl = task._effective_deadline
        dl_str = format_date(eff_dl)
        dl_color = COLORS["text_dim"]
        if task._effective_deadline_date and task._effective_deadline_date < today and task.status.lower() not in ("completed", "done"):
            dl_color = COLORS["error"]

        status_color = COLORS["success"] if task.status.lower() in ("completed", "done") else (COLORS["info"] if task.status.lower() == "active" else COLORS["warning"])
        prio_color = COLORS["error"] if task.priority.lower() in ("high", "urgent") else (COLORS["warning"] if task.priority.lower() in ("medium", "normal") else COLORS["text_dim"])

        # In-place label updates
        if info["lbl_status"].cget("text") != task.status.upper():
            info["lbl_status"].configure(text=task.status.upper(), text_color=status_color)
            if not user_interacting:
                self._pulse_card_border(info["inner_card"])

        if info["lbl_dl"].cget("text") != f"Due: {dl_str}":
            info["lbl_dl"].configure(text=f"Due: {dl_str}", text_color=dl_color)

        if info["lbl_prio"].cget("text") != task.priority.upper():
            info["lbl_prio"].configure(text=task.priority.upper(), text_color=prio_color)

        if info["lbl_desc"].cget("text") != task.description:
            info["lbl_desc"].configure(text=task.description)

        # Combobox selection is preserved! If the employee picked a status, info["status_var"].get() remains intact.

    def _create_task_row(self, task, today, is_brand_new=False):
        """Creates a single task row widget and triggers entrance animations if newly added."""
        row = ctk.CTkFrame(self.tasks_container, fg_color="transparent", border_width=0)
        row.grid_columnconfigure(0, weight=1)

        start_bg = "#EFF6FF" if is_brand_new else COLORS["card_bg"]
        start_border = "#3B82F6" if is_brand_new else COLORS["border"]
        border_w = 2 if is_brand_new else 1

        inner = ctk.CTkFrame(row, fg_color=start_bg, border_width=border_w,
                             border_color=start_border, corner_radius=8)
        inner.grid(row=0, column=0, sticky="ew", pady=2)
        inner.grid_columnconfigure(1, weight=1)

        def bind_events(widget, t=task):
            widget.bind("<Double-1>", lambda event, tk=t: self.show_task_details_dialog(tk))

        bind_events(inner)

        left_info = ctk.CTkFrame(inner, fg_color="transparent")
        left_info.grid(row=0, column=0, padx=20, pady=16, sticky="w")
        bind_events(left_info)

        new_badge = None
        if is_brand_new:
            new_badge = ctk.CTkLabel(left_info, text="✨ NEW", font=("Segoe UI", 9, "bold"),
                                     text_color="#1D4ED8", fg_color="#DBEAFE", corner_radius=4,
                                     width=52, height=18)
            new_badge.pack(anchor="w", pady=(0, 2))

        short_id = str(task.task_id)[-4:] if getattr(task, 'task_id', None) else ""
        lbl_id = ctk.CTkLabel(left_info, text=short_id, font=FONTS["small"], text_color=COLORS["text_dim"])
        lbl_id.pack(anchor="w")
        bind_events(lbl_id)

        prio_color = COLORS["error"] if task.priority.lower() in ("high", "urgent") else (COLORS["warning"] if task.priority.lower() in ("medium", "normal") else COLORS["text_dim"])
        lbl_prio = ctk.CTkLabel(left_info, text=task.priority.upper(), font=("Segoe UI", 9), text_color=prio_color)
        lbl_prio.pack(anchor="w", pady=(2, 0))
        bind_events(lbl_prio)

        mid_info = ctk.CTkFrame(inner, fg_color="transparent")
        mid_info.grid(row=0, column=1, padx=16, pady=16, sticky="nsew")
        bind_events(mid_info)
        lbl_desc = ctk.CTkLabel(mid_info, text=task.description, font=("Segoe UI", 14), text_color=COLORS["text_main"], justify="left", wraplength=450, anchor="w")
        lbl_desc.pack(anchor="w", fill="both", expand=True)
        bind_events(lbl_desc)

        right_info = ctk.CTkFrame(inner, fg_color="transparent")
        right_info.grid(row=0, column=2, padx=20, pady=16, sticky="e")
        bind_events(right_info)

        eff_dl = task._effective_deadline
        dl_str = format_date(eff_dl)
        dl_color = COLORS["text_dim"]
        if task._effective_deadline_date and task._effective_deadline_date < today and task.status.lower() not in ("completed", "done"):
            dl_color = COLORS["error"]

        lbl_dl = ctk.CTkLabel(right_info, text=f"Due: {dl_str}", font=FONTS["small"], text_color=dl_color)
        lbl_dl.pack(anchor="e", pady=(0, 4))
        bind_events(lbl_dl)

        status_color = COLORS["success"] if task.status.lower() in ("completed", "done") else (COLORS["info"] if task.status.lower() == "active" else COLORS["warning"])
        lbl_status = ctk.CTkLabel(right_info, text=task.status.upper(), font=("Segoe UI", 10), text_color=status_color)
        lbl_status.pack(anchor="e")
        bind_events(lbl_status)

        actions_frame = ctk.CTkFrame(inner, fg_color="transparent")
        actions_frame.grid(row=0, column=3, padx=20, pady=16, sticky="e")

        has_checklist = bool(getattr(task, 'checklist', None))
        combo_values = ["Completed", "Delayed", "Update"] if has_checklist else ["Completed", "Delayed"]

        # Restore any pending selection from the employee
        initial_val = self._user_dropdown_selections.get(task.task_id, "Status...")
        status_var = ctk.StringVar(value=initial_val)

        status_combo = ModernComboBox(actions_frame, values=combo_values,
                                      variable=status_var, width=140, height=32, font=FONTS["small"], dropdown_font=FONTS["small"],
                                      corner_radius=6)
        status_combo.pack(side="left", padx=(0, 8))

        def on_combo_changed(val, t_id=task.task_id):
            self._user_dropdown_selections[t_id] = val
        status_combo.configure(command=on_combo_changed)

        btn_action = ctk.CTkButton(actions_frame, text="Update", width=90, height=32, font=FONTS["small"], corner_radius=6,
                                   fg_color=COLORS["accent"], text_color="#FFFFFF", hover_color=COLORS["accent_hover"])

        def handle_action(t=task, c=status_combo, b=btn_action):
            val = c.get()
            if val == "Update":
                if has_checklist:
                    self.show_task_details_dialog(t, checklist_only=True)
                return
            elif val and val != "Status...":
                self.do_inline_update(t, val, b)

        btn_action.configure(command=handle_action)
        btn_action.pack(side="left", padx=(0, 8))

        btn_view = ctk.CTkButton(actions_frame, text="View", width=60, height=32, font=FONTS["small"], corner_radius=6,
                                 fg_color="transparent", border_width=1, border_color=COLORS["border"],
                                 text_color=COLORS["text_main"], hover_color=COLORS["bg"],
                                 command=lambda t=task: self.show_task_details_dialog(t))
        btn_view.pack(side="left")

        row_info = {
            "row_widget": row,
            "inner_card": inner,
            "task": task,
            "status_combo": status_combo,
            "status_var": status_var,
            "btn_action": btn_action,
            "lbl_status": lbl_status,
            "lbl_dl": lbl_dl,
            "lbl_prio": lbl_prio,
            "lbl_desc": lbl_desc,
            "has_checklist": has_checklist,
            "new_badge": new_badge
        }

        if is_brand_new:
            self._animate_new_task_row(row, inner, new_badge)

        return row_info

    def _animate_new_task_row(self, row, inner, new_badge):
        """Animates a newly added task row with height expansion and a luminous highlight fade."""
        target_height = 80
        row.grid_propagate(False)
        row.configure(height=10)

        def step_expand(current_h=10):
            if not row.winfo_exists():
                return
            if current_h < target_height:
                next_h = current_h + 14
                row.configure(height=min(next_h, target_height))
                self.after(16, lambda: step_expand(next_h))
            else:
                row.grid_propagate(True)

        self.after(10, step_expand)

        def step_color(step=0, total_steps=22):
            if not inner.winfo_exists():
                return
            factor = step / total_steps
            eased = 1 - (1 - factor) ** 2  # smooth ease-out
            bg = _interpolate_color("#EFF6FF", COLORS["card_bg"], eased)
            border = _interpolate_color("#3B82F6", COLORS["border"], eased)
            try:
                inner.configure(fg_color=bg, border_color=border)
            except Exception:
                pass
            if step < total_steps:
                self.after(45, lambda: step_color(step + 1, total_steps))
            else:
                try:
                    inner.configure(fg_color=COLORS["card_bg"], border_color=COLORS["border"], border_width=1)
                except Exception:
                    pass

        self.after(180, step_color)

        if new_badge:
            def remove_badge():
                if new_badge.winfo_exists():
                    new_badge.destroy()
            self.after(4000, remove_badge)

    def _pulse_card_border(self, inner):
        """Subtle 700ms pulse border when an existing task is remotely updated."""
        try:
            inner.configure(border_color="#3B82F6", border_width=2)
            def revert():
                if inner.winfo_exists():
                    inner.configure(border_color=COLORS["border"], border_width=1)
            self.after(700, revert)
        except Exception:
            pass


    # ── Task Detail Dialog ───────────────────────────────────────────────

    def show_task_details_dialog(self, task, checklist_only=False):
        dialog = ctk.CTkToplevel(self)
        dialog.attributes("-alpha", 0.0)
        dialog.title("Checklist" if checklist_only else f"Task Details: {task.task_id}")
        dialog.geometry("700x600")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (700 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (600 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        fade_in(dialog)

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        eff_dl = getattr(task, "_effective_deadline", task.deadline)
        is_ext = getattr(task, "_is_extended", False)

        if not checklist_only:
            short_id = str(task.task_id)[-4:] if getattr(task, 'task_id', None) else ""
            details = [
                ("Task ID", short_id),
                ("Date Assigned", format_date(task.date)),
                ("Current Deadline", format_date(eff_dl) + (" (Extended)" if is_ext else "")),
            ]
            if is_ext:
                details.append(("Original Deadline", format_date(task.deadline)))
            details.extend([
                ("Assigned To", task.assigned_to),
                ("Assigned By", task.assigned_by),
                ("Priority", task.priority),
                ("Status", task.status),
                ("Reason", task.reason),
                ("Source", task.source),
                ("Last Updated", task.last_updated),
            ])
    
            for label, value in details:
                ctk.CTkLabel(scroll, text=f"{label}:", font=FONTS["body"],
                             text_color=COLORS["text_main"]).pack(anchor="w", pady=(10, 0))
                ctk.CTkLabel(scroll, text=str(value) if value else "N/A", font=FONTS["body"],
                             text_color=COLORS["text_dim"], wraplength=450,
                             justify="left").pack(anchor="w")
    
            ctk.CTkLabel(scroll, text="Description:", font=FONTS["body"],
                         text_color=COLORS["text_main"]).pack(anchor="w", pady=(10, 0))
            desc_box = ctk.CTkTextbox(scroll, height=120, font=FONTS["body"],
                                      text_color=COLORS["text_dim"], fg_color=COLORS["input_bg"])
            desc_box.insert("1.0", str(task.description))
            desc_box.configure(state="disabled")
            desc_box.pack(fill="x", pady=(5, 10))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20, padx=20)
        
        btn_complete = None
        checkbox_vars = []

        if getattr(task, 'checklist', None):
            ctk.CTkLabel(scroll, text="Checklist:", font=FONTS["body"],
                         text_color=COLORS["text_main"]).pack(anchor="w", pady=(10, 0))
            chk_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            chk_frame.pack(fill="x", pady=(5, 10))
            
            def check_all_completed():
                return all(v.get() for v in checkbox_vars)
                
            def update_complete_btn():
                if not btn_complete: return
                if check_all_completed() and task.status.lower() not in ("completed", "done"):
                    btn_complete.configure(state="normal", fg_color=COLORS["success"])
                else:
                    btn_complete.configure(state="disabled", fg_color=COLORS["border"])

            for i, item in enumerate(task.checklist):
                is_checked = False
                text = str(item)
                if isinstance(item, dict):
                    is_checked = item.get("completed", False)
                    text = str(item.get("text", "")) or str(item.get("step", ""))
                elif isinstance(item, str):
                    if item.startswith("[x]"):
                        is_checked = True
                        text = item[3:].strip()
                    elif item.startswith("[ ]"):
                        text = item[3:].strip()
                
                var = ctk.BooleanVar(value=is_checked)
                checkbox_vars.append(var)
                
                item_card = ctk.CTkFrame(chk_frame, fg_color=COLORS["input_bg"], corner_radius=6, border_width=1, border_color=COLORS["border"])
                item_card.pack(fill="x", pady=4, ipady=4)
                item_card.grid_columnconfigure(1, weight=1)
                
                lbl = ctk.CTkLabel(item_card, text=text, font=FONTS["body"], text_color=COLORS["text_dim"] if is_checked else COLORS["text_main"], justify="left", wraplength=600, anchor="w")
                
                def on_toggle(idx=i, v=var, t=task, l=lbl):
                    new_state = v.get()
                    l.configure(text_color=COLORS["text_dim"] if new_state else COLORS["text_main"])
                    if isinstance(t.checklist[idx], dict):
                        t.checklist[idx]["completed"] = new_state
                    elif isinstance(t.checklist[idx], str):
                        prefix = "[x]" if new_state else "[ ]"
                        base_text = str(t.checklist[idx])
                        if base_text.startswith("[x]") or base_text.startswith("[ ]"):
                            base_text = base_text[3:].strip()
                        t.checklist[idx] = f"{prefix} {base_text}"
                    update_complete_btn()
                    threading.Thread(target=lambda: (self.sheets_client.update_task_checklist(t.task_id, t.checklist), self.after(0, self._full_refresh)), daemon=True).start()
                
                chk = ctk.CTkCheckBox(item_card, text="", variable=var, command=on_toggle, width=24)
                chk.grid(row=0, column=0, padx=(10, 5), pady=8, sticky="n")
                
                lbl.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="w")
                
            if task.status.lower() not in ("completed", "done", "update"):
                btn_complete = ctk.CTkButton(btn_frame, text="Completed", font=FONTS["body"], height=38, text_color="#FFFFFF")
                btn_complete.pack(side="left", expand=True, padx=(0, 10))
                
                def on_complete_click(t=task, b=btn_complete):
                    self.do_inline_update(t, "Completed", b)
                    dialog.destroy()
                    
                btn_complete.configure(command=on_complete_click)
                update_complete_btn()

        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, height=38,
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"]).pack(side="right", expand=True)

    # ── Extension Request Dialog ─────────────────────────────────────────

    def prompt_extension_request(self, task, var):
        dialog = ctk.CTkToplevel(self)
        dialog.attributes("-alpha", 0.0)
        dialog.title("Request Deadline Extension")
        dialog.geometry("540x580")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (540 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (580 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        fade_in(dialog)

        short_id = str(task.task_id)[-4:] if getattr(task, 'task_id', None) else ""
        ctk.CTkLabel(dialog, text=f"Task: [{short_id}]", font=FONTS["body"],
                     text_color=COLORS["text_main"]).pack(pady=(20, 2), padx=20, anchor="w")
        ctk.CTkLabel(dialog, text=f"Current Deadline: {format_date(task.deadline)}",
                     font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=(0, 10), padx=20, anchor="w")

        ctk.CTkLabel(dialog, text="Reason for Extension:", font=FONTS["body"],
                     text_color=COLORS["text_main"]).pack(pady=(5, 3), padx=20, anchor="w")
        reason_text = ctk.CTkTextbox(dialog, height=90, font=FONTS["body"],
                                     text_color=COLORS["text_main"], fg_color=COLORS["input_bg"],
                                     border_color=COLORS["border"], border_width=1)
        reason_text.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(dialog, text="Requested New Deadline:", font=FONTS["body"],
                     text_color=COLORS["text_main"]).pack(pady=(5, 3), padx=20, anchor="w")
        deadline_entry = DateEntry(dialog, width=28, date_pattern='dd/mm/yyyy',
                                   background=COLORS["sidebar_bg"], foreground='white',
                                   borderwidth=2, font=FONTS["body"])
        deadline_entry.pack(padx=20, pady=(0, 10), anchor="w")

        ctk.CTkLabel(dialog, text="⚠ Your request will be sent to the manager for approval.",
                     font=FONTS["small"], text_color=COLORS["warning"], wraplength=500, justify="left").pack(padx=20, pady=(0, 10), anchor="w")

        def submit():
            reason = reason_text.get("1.0", "end").strip()
            new_deadline = deadline_entry.get()
            if not reason:
                messagebox.showwarning("Missing Info", "Please provide a reason for the extension.")
                return
            person_name = self.current_user
            
            for child in btn_frame.winfo_children():
                if isinstance(child, ctk.CTkButton) and child.cget("text") == "Submit Request":
                    child.configure(state="disabled")

            def submit_thread():
                try:
                    req_id = submit_extension_request(
                        task_id=task.task_id, task_description=task.description,
                        employee_name=person_name, current_deadline=task.deadline,
                        requested_deadline=new_deadline, reason=reason,
                        department=self.current_dept or "")
                    self.after(0, lambda: on_submit_success(req_id))
                except Exception as e:
                    self.after(0, lambda: on_submit_error(e))

            def on_submit_success(req_id):
                self.modified_task_info[task.task_id] = {
                    "reason": f"{reason} (Old Deadline: {task.deadline}) [Extension Request: {req_id}]",
                    "deadline": task.deadline
                }
                dialog.destroy()
                messagebox.showinfo("Request Sent",
                                    f"Extension request [{req_id}] has been submitted.\n"
                                    "The manager will review it on the dashboard.")
                self._full_refresh()
                
            def on_submit_error(e):
                messagebox.showerror("Error", f"Failed to submit request:\n{e}")
                for child in btn_frame.winfo_children():
                    if isinstance(child, ctk.CTkButton) and child.cget("text") == "Submit Request":
                        child.configure(state="normal")
            
            threading.Thread(target=submit_thread, daemon=True).start()

        def cancel():
            var.set(task.status)
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", cancel)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 20))
        ctk.CTkButton(btn_frame, text="Submit Request", command=submit,
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      font=FONTS["body"], height=40, width=140).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_frame, text="Cancel", command=cancel,
                      fg_color="transparent", border_width=1, border_color=COLORS["border"],
                      text_color=COLORS["text_main"], hover_color=COLORS["card_bg"],
                      font=FONTS["body"], height=40, width=100).pack(side="right")

    # ── Extension Requests Display ───────────────────────────────────────

    def _update_extension_display(self, ext_requests):
        """Seamlessly updates extension request cards in place."""
        current_ext_scroll = None
        try:
            current_ext_scroll = self.ext_container._parent_canvas.yview()[0]
        except Exception:
            pass

        if not ext_requests:
            for card in self._ext_rows.values():
                card["widget"].pack_forget()
            if hasattr(self, "empty_ext_frame"):
                self.empty_ext_frame.pack(pady=40)
            return

        if hasattr(self, "empty_ext_frame"):
            self.empty_ext_frame.pack_forget()

        req_list = list(reversed(ext_requests))
        target_keys = set()

        for idx, req in enumerate(req_list):
            key = str(req.get("id") or f"{req.get('task_id')}_{req.get('requested_deadline')}")
            target_keys.add(key)

            status = req.get("status", "Pending")
            if status == "Pending":
                badge_color, badge_text = COLORS["warning"], "PENDING"
            elif status == "Approved":
                badge_color, badge_text = COLORS["success"], "APPROVED"
            else:
                badge_color, badge_text = COLORS["error"], "REJECTED"

            final_deadline = format_date(req.get("manager_deadline") or req.get("requested_deadline"))
            if status == "Approved":
                dl_lbl = f"New Deadline: {final_deadline}"
            elif status == "Rejected":
                dl_lbl = f"Unchanged: {format_date(req.get('current_deadline'))}"
            else:
                dl_lbl = f"Requested: {format_date(req.get('requested_deadline'))}"

            desc = req.get("task_description", "")
            if len(desc) > 40:
                desc = desc[:40] + "..."

            note_text = f"Note: {req.get('manager_note')}" if status != "Pending" and req.get("manager_note") else ""

            if key in self._ext_rows:
                # Update existing card
                card_info = self._ext_rows[key]
                card_info["lbl_badge"].configure(text=badge_text, fg_color=badge_color)
                card_info["lbl_dl"].configure(text=dl_lbl)
                if note_text:
                    card_info["lbl_note"].configure(text=note_text)
                    card_info["lbl_note"].pack(anchor="w", padx=16, pady=(0, 12))
                else:
                    card_info["lbl_note"].pack_forget()
                card_info["widget"].pack(fill="x", pady=6)
            else:
                # Create new extension request card
                card = ctk.CTkFrame(self.ext_container, fg_color="transparent", border_width=1, border_color=COLORS["border"], corner_radius=8)
                card.pack(fill="x", pady=6)

                top_row = ctk.CTkFrame(card, fg_color="transparent")
                top_row.pack(fill="x", padx=16, pady=(16, 8))

                lbl_badge = ctk.CTkLabel(top_row, text=badge_text, font=("Segoe UI", 9),
                                         text_color="#FFFFFF", fg_color=badge_color, corner_radius=4,
                                         width=70, height=22)
                lbl_badge.pack(side="left")

                ctk.CTkLabel(card, text=req.get("task_id", ""), font=FONTS["body"], text_color=COLORS["text_main"]).pack(anchor="w", padx=16)
                ctk.CTkLabel(card, text=desc, font=FONTS["body"], text_color=COLORS["text_dim"]).pack(anchor="w", padx=16, pady=(4, 12))

                bot_row = ctk.CTkFrame(card, fg_color=COLORS["bg"], corner_radius=0)
                bot_row.pack(fill="x", padx=1, pady=(0, 1))

                lbl_dl = ctk.CTkLabel(bot_row, text=dl_lbl, font=FONTS["body"], text_color=COLORS["text_main"])
                lbl_dl.pack(anchor="w", padx=16, pady=10)

                lbl_note = ctk.CTkLabel(card, text=note_text, font=FONTS["small"], text_color=COLORS["text_dim"], wraplength=220)
                if note_text:
                    lbl_note.pack(anchor="w", padx=16, pady=(0, 12))

                self._ext_rows[key] = {
                    "widget": card,
                    "lbl_badge": lbl_badge,
                    "lbl_dl": lbl_dl,
                    "lbl_note": lbl_note
                }

        # Hide cards no longer in data
        for k in list(self._ext_rows.keys()):
            if k not in target_keys:
                self._ext_rows[k]["widget"].pack_forget()

        if current_ext_scroll is not None:
            try:
                self.after_idle(lambda: self.ext_container._parent_canvas.yview_moveto(current_ext_scroll))
            except Exception:
                pass


    # ── Add Task Dialog (self-assign only) ───────────────────────────────

    def _show_add_task_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.attributes("-alpha", 0.0)
        dialog.title("Add New Task")
        dialog.geometry("520x560")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (520 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (560 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        fade_in(dialog)

        form = ctk.CTkFrame(dialog, fg_color=COLORS["card_bg"], corner_radius=8)
        form.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(form, text="Create a Task for Yourself", font=FONTS["subheader"],
                     text_color=COLORS["text_main"]).pack(pady=(20, 15), padx=20, anchor="w")

        # Assigned To (read-only — always self)
        row1 = ctk.CTkFrame(form, fg_color="transparent")
        row1.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(row1, text="Assigned To:", font=FONTS["body"],
                     text_color=COLORS["text_main"], width=140, anchor="w").pack(side="left")
        ctk.CTkLabel(row1, text=self.current_user, font=FONTS["body"],
                     text_color=COLORS["accent"]).pack(side="left", padx=5)

        # Task Description
        ctk.CTkLabel(form, text="Task Description:", font=FONTS["body"],
                     text_color=COLORS["text_main"]).pack(padx=20, pady=(10, 3), anchor="w")
        task_desc = ctk.CTkTextbox(form, height=100, font=FONTS["body"],
                                   text_color=COLORS["text_main"], fg_color=COLORS["input_bg"],
                                   border_color=COLORS["border"], border_width=1)
        task_desc.pack(fill="x", padx=20, pady=(0, 10))

        # Deadline
        row_dl = ctk.CTkFrame(form, fg_color="transparent")
        row_dl.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(row_dl, text="Deadline:", font=FONTS["body"],
                     text_color=COLORS["text_main"], width=140, anchor="w").pack(side="left")
        dl_entry = DateEntry(row_dl, width=20, date_pattern='dd/mm/yyyy',
                             background=COLORS["sidebar_bg"], foreground='white',
                             borderwidth=2, font=FONTS["body"])
        dl_entry.pack(side="left")

        # Priority
        row_prio = ctk.CTkFrame(form, fg_color="transparent")
        row_prio.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(row_prio, text="Priority:", font=FONTS["body"],
                     text_color=COLORS["text_main"], width=140, anchor="w").pack(side="left")
        prio_combo = ModernComboBox(row_prio, values=["Low", "Normal", "High", "Urgent"],
                                    width=200, height=36, font=FONTS["body"],
                                    dropdown_font=FONTS["body"], corner_radius=6)
        prio_combo.set("Normal")
        prio_combo.pack(side="left")

        def submit_task():
            desc_text = task_desc.get("1.0", "end").strip()
            deadline = dl_entry.get()
            priority = prio_combo.get()

            if not desc_text:
                messagebox.showwarning("Missing Info", "Please enter a task description.")
                return

            today_str = datetime.now().strftime("%d/%m/%Y")
            payload = {
                self.current_user: [
                    {
                        "goal": desc_text,
                        "date": today_str,
                        "deadline": deadline,
                        "priority": priority,
                    }
                ]
            }

            try:
                success = self.n8n_client.submit_daily_goals(payload)
                if success:
                    dialog.destroy()
                    messagebox.showinfo("Success", "Task created successfully!")
                    self._full_refresh()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create task:\n{e}")

        # Buttons
        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(15, 20))
        ctk.CTkButton(btn_row, text="Create Task", command=submit_task,
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      font=FONTS["body"], height=42, width=160).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_row, text="Cancel", command=dialog.destroy,
                      fg_color="transparent", border_width=1, border_color=COLORS["border"],
                      text_color=COLORS["text_main"], hover_color=COLORS["card_bg"],
                      font=FONTS["body"], height=42, width=100).pack(side="right")

    # ── Data Fetch ───────────────────────────────────────────────────────

    def _fetch_tasks_data(self):
        person_name = self.current_user
        if not person_name:
            return
        try:
            tasks = self.sheets_client.fetch_tasks_for_employee(person_name)
            recent_updates = load_recent_updates()
            for t in tasks:
                if t.task_id in recent_updates:
                    t.status = recent_updates[t.task_id]["status"]
                    if "reason" in recent_updates[t.task_id]:
                        t.reason = recent_updates[t.task_id]["reason"]
            self.current_tasks = tasks
        except Exception as e:
            if not hasattr(self, 'current_tasks') or self.current_tasks is None:
                self.current_tasks = []
            print(f"Fetch failed (retaining cached view): {e}")

    def _full_refresh(self):
        """Re-fetch data and update the dashboard in-place seamlessly."""
        self._trigger_fetch(is_background=False)

    def _start_auto_refresh(self):
        """Auto-refresh every 30s to pick up changes seamlessly without screen recreation."""
        _AUTO_REFRESH_MS = 30_000
        def _tick():
            try:
                self._trigger_fetch(is_background=True)
            except Exception:
                pass
            self.after(_AUTO_REFRESH_MS, _tick)
        self.after(_AUTO_REFRESH_MS, _tick)

    # ── Submit Updates ───────────────────────────────────────────────────

    def do_inline_update(self, task, new_status, btn_widget):
        if not new_status or new_status == "Status...":
            return
            
        if new_status == "Completed" and getattr(task, 'checklist', None):
            all_completed = True
            for item in task.checklist:
                if isinstance(item, dict) and not item.get("completed"):
                    all_completed = False
                elif isinstance(item, str) and not item.startswith("[x]"):
                    all_completed = False
            
            if not all_completed:
                messagebox.showwarning("Incomplete Checklist", "You cannot mark this task as complete until all checklist items are ticked.")
                return

        if new_status == "Delayed":
            dummy_var = ctk.StringVar(value=task.status)
            self.prompt_extension_request(task, dummy_var)
            return

        if new_status != task.status:
            task_dict = {
                "Task ID": task.task_id,
                "Date": task.date,
                "Task Description": task.description,
                "Assigned To": task.assigned_to,
                "Assigned By": task.assigned_by,
                "Deadline": task.deadline,
                "Priority": task.priority,
                "Status": new_status,
                "Reason": task.reason,
                "Source": task.source,
                "Updated By": "UI Input",
                "Last Updated": task.last_updated
            }
            
            btn_widget.configure(state="disabled")
            
            def update_thread():
                try:
                    success = self.n8n_client.submit_live_updates([task_dict])
                    self.after(0, lambda: on_update_success(success))
                except Exception as e:
                    self.after(0, lambda: on_update_error(e))

            def on_update_success(success):
                if success:
                    messagebox.showinfo("Success", f"Task {task.task_id} updated to {new_status}.")
                    recent_updates = load_recent_updates()
                    recent_updates[task.task_id] = {
                        "status": new_status,
                        "reason": task.reason,
                        "timestamp": time.time()
                    }
                    save_recent_updates(recent_updates)
                    # Write optimistic override so Admin Dashboard sees it instantly
                    record_task_update(task.task_id, {
                        "Status": new_status,
                        "Reason": task.reason,
                        "Updated By": "UI Input",
                        "Last Updated": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    })
                    self._user_dropdown_selections.pop(task.task_id, None)
                    if task.task_id in self._task_rows:
                        self._task_rows[task.task_id]["status_var"].set("Status...")
                    self._full_refresh()
                try:
                    btn_widget.configure(state="normal")
                except:
                    pass
            
            def on_update_error(e):
                messagebox.showerror("Error", f"Failed to update task:\n{e}")
                try:
                    btn_widget.configure(state="normal")
                except:
                    pass

            threading.Thread(target=update_thread, daemon=True).start()


if __name__ == "__main__":
    app = TaskUpdaterApp()
    app.mainloop()
