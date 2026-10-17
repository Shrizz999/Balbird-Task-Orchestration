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
import config
from config import COLORS, FONTS, DEPARTMENTS, SHOW_MEETING_TRANSCRIPTS
# UI Feature Flag: Controls Meeting Transcript visibility in Employee Portal.
# To bring meeting transcript back, set SHOW_MEETING_TRANSCRIPTS = True in config.py (or override here: config.SHOW_MEETING_TRANSCRIPTS = True)

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
from services.notifier import (
    notify_employee_new_task,
    notify_employee_extension_resolved,
    notify_employee_task_overdue,
)
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


class ModernFilterBar(ctk.CTkFrame):
    """Sleek, modern pill-style filter bar with zero background boxiness and crisp active borders."""
    def __init__(self, master, values, default_val=None, command=None, color_map=None, btn_width=None, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self.values = values
        self.command = command
        self.color_map = color_map or {}
        self._current_value = default_val or (values[0] if values else "")
        self._buttons = {}

        for val in values:
            calc_w = btn_width if btn_width is not None else max(44, int(len(val) * 7.2 + 22))
            btn = ctk.CTkButton(
                self, text=val, width=calc_w, height=32, corner_radius=16,
                font=FONTS["small"], cursor="hand2",
                command=lambda v=val: self._on_btn_click(v)
            )
            btn.pack(side="left", padx=2)
            self._buttons[val] = btn

        self._render_state()

    def _on_btn_click(self, val):
        self._current_value = val
        self._render_state()
        if self.command:
            self.command(val)

    def _render_state(self):
        hover_tints = {
            "#64748B": "#F1F5F9",
            "#2563EB": "#EFF6FF",
            "#D97706": "#FFFBEB",
            "#DC2626": "#FEF2F2"
        }
        for val, btn in self._buttons.items():
            active_color = self.color_map.get(val, COLORS["accent"])
            active_hover = hover_tints.get(active_color, "#EFF6FF")
            if val == self._current_value:
                btn.configure(
                    fg_color="transparent",
                    border_width=1.5,
                    border_color=active_color,
                    text_color=active_color,
                    hover_color=active_hover,
                    font=(FONTS["small"][0], FONTS["small"][1], "bold")
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    border_width=1,
                    border_color=COLORS["border"],
                    text_color=COLORS["text_dim"],
                    hover_color="#F8FAFC",
                    font=FONTS["small"]
                )

    def get(self):
        return self._current_value

    def set(self, val):
        if val in self._buttons:
            self._current_value = val
            self._render_state()


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
    SHOW_KPIS = False  # Set to True to display KPIs, or toggle at runtime via self.toggle_kpis()

    def __init__(self):
        super().__init__()
        self.attributes("-alpha", 0.0)
        ctk.set_appearance_mode("Light")
        self.title("Balbird TO - Employee Portal")
        self.geometry("1300x900")
        self.minsize(1150, 750)
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
        self.show_kpis = self.SHOW_KPIS  # Controls KPI section visibility

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
        """Builds static TO-DO section, KPI bar and independent scrollable containers for tasks and extensions."""
        # 0. TO-DO Section (Action Required — Next Up, 3 tasks max)
        self.todo_outer = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.todo_outer.pack(fill="x", pady=(0, 14))
        self._init_todo_section()

        # 1. KPI Outer Frame (Kept in memory, hidden by default; can be shown anytime via toggle_kpis or SHOW_KPIS)
        self.kpi_outer = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.kpi_labels = {}

        cards_data = [
            ("total",              "Total Tasks",      "-"),
            ("active",             "Active",           "-"),
            ("completed",          "Completed",        "-"),
            ("overdue",            "Overdue",          "-"),
            ("due_today",          "Due Today",        "-"),
            ("due_this_week",      "Due This Week",    "-"),
            ("high_priority",      "High / Urgent",    "-"),
            ("pending_extensions", "Pending Ext.",     "-"),
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
                key, label, val_default = cards_data[i]
                card = ctk.CTkFrame(row_frame, fg_color=COLORS["card_bg"],
                                    corner_radius=10, border_width=1, border_color=COLORS["border"])
                card.grid(row=0, column=col_idx, sticky="nsew", padx=6, pady=2)

                # Blue accent at top edge
                top_edge = ctk.CTkFrame(card, fg_color=COLORS["accent"], height=4, corner_radius=2)
                top_edge.pack(fill="x", side="top", padx=0, pady=0)
                top_edge.pack_propagate(False)

                lbl_val = ctk.CTkLabel(card, text=val_default, font=(FONTS["header"][0], 22, "bold"),
                                       text_color=COLORS["text_main"], fg_color="transparent")
                lbl_val.pack(anchor="w", padx=16, pady=(10, 0))
                self.kpi_labels[key] = lbl_val

                ctk.CTkLabel(card, text=label, font=FONTS["small"],
                             text_color=COLORS["text_dim"], fg_color="transparent").pack(anchor="w", padx=16, pady=(2, 10))

        if getattr(self, "show_kpis", False):
            self.kpi_outer.pack(fill="x", pady=(0, 14))

        # 2. Main Two-Column Frame (Fills all remaining vertical height)
        self.columns_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.columns_frame.pack(fill="both", expand=True)
        self.columns_frame.grid_columnconfigure(0, weight=75)
        self.columns_frame.grid_columnconfigure(1, weight=25)
        self.columns_frame.grid_rowconfigure(0, weight=1)

        left_col = ctk.CTkFrame(self.columns_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        right_col = ctk.CTkFrame(self.columns_frame, fg_color="transparent")
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
            width=180, height=34, font=FONTS["small"], fg_color="#FFFFFF",
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

        self.filter_combo = ModernFilterBar(
            toolbar, values=["Active", "All", "Completed", "Overdue", "Delayed", "High Priority"],
            default_val=self._filter_status,
            command=lambda _: self._on_sort_filter_change()
        )
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

    def toggle_kpis(self, visible=None):
        """Toggle or set visibility of the KPI section.
        Usage:
            app.toggle_kpis()      # Toggles visibility on/off
            app.toggle_kpis(True)  # Shows KPIs
            app.toggle_kpis(False) # Hides KPIs
        """
        if visible is None:
            self.show_kpis = not getattr(self, "show_kpis", False)
        else:
            self.show_kpis = bool(visible)

        if hasattr(self, "kpi_outer") and self.kpi_outer.winfo_exists():
            if self.show_kpis:
                if hasattr(self, "todo_outer") and self.todo_outer.winfo_manager() == "pack":
                    self.kpi_outer.pack(fill="x", pady=(0, 14), after=self.todo_outer)
                elif hasattr(self, "columns_frame") and self.columns_frame.winfo_manager() == "pack":
                    self.kpi_outer.pack(fill="x", pady=(0, 14), before=self.columns_frame)
                else:
                    self.kpi_outer.pack(fill="x", pady=(0, 14))
            else:
                self.kpi_outer.pack_forget()

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

        # 2. Update TO-DO section in-place (top 3 prioritized tasks)
        self._update_todo_section(all_tasks, today)

        # 3. Update task cards in-place with diffing & smooth entrance animation
        self._update_tasks_display(all_tasks, today)

        # 4. Update extension request cards in-place
        self._update_extension_display(ext_requests)

        # 5. Check and dispatch native Windows Action Center notifications
        self._check_employee_notifications(all_tasks, ext_requests, today)

    def _check_employee_notifications(self, all_tasks, ext_requests, today):
        """Dispatches native Windows Action Center notifications for new tasks, approved extensions, and overdue alerts."""
        if not hasattr(self, "_known_notif_tasks"):
            # Seed on initial load so we don't spam toasts on startup
            self._known_notif_tasks = {t.task_id for t in all_tasks}
            self._known_ext_statuses = {str(req.get("id") or req.get("task_id")): req.get("status", "") for req in ext_requests}
            return

        # 1. New Task Assigned Alert
        current_ids = {t.task_id for t in all_tasks}
        new_ids = current_ids - self._known_notif_tasks
        for t in all_tasks:
            if t.task_id in new_ids and str(t.status).strip().lower() not in ("completed", "done"):
                notify_employee_new_task(t)
        self._known_notif_tasks.update(current_ids)

        # 2. Extension Approved / Rejected Alert
        for req in ext_requests:
            req_id = str(req.get("id") or req.get("task_id"))
            current_status = req.get("status", "")
            prev_status = self._known_ext_statuses.get(req_id)
            if prev_status == "Pending" and current_status in ("Approved", "Rejected"):
                new_dl = req.get("manager_deadline") or req.get("requested_deadline", "")
                notify_employee_extension_resolved(req.get("task_id", ""), current_status, new_dl)
            self._known_ext_statuses[req_id] = current_status

        # 3. Overdue / At-Risk Alert
        for t in all_tasks:
            if str(t.status).strip().lower() not in ("completed", "done") and t._effective_deadline_date and t._effective_deadline_date < today:
                overdue_days = (today - t._effective_deadline_date).days
                notify_employee_task_overdue(t, overdue_days)

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

    # ═════════════════════════════════════════════════════════════════════
    # TO-DO Section (Next Up — Top 3 Industrial SLA Prioritized)
    # ═════════════════════════════════════════════════════════════════════

    def _init_todo_section(self):
        """Builds static TO-DO (Next Up) container with 3 prioritized task slots."""
        hdr_frame = ctk.CTkFrame(self.todo_outer, fg_color="transparent")
        hdr_frame.pack(fill="x", pady=(0, 8))

        hdr_left = ctk.CTkFrame(hdr_frame, fg_color="transparent")
        hdr_left.pack(side="left")

        ctk.CTkLabel(hdr_left, text="🎯 Action Required — Next Up",
                     font=(FONTS["header"][0], 14, "bold"),
                     text_color=COLORS["text_main"]).pack(side="left")

        ctk.CTkLabel(hdr_left, text="• Top 3 prioritized by industrial SLA, deadlines & urgency",
                     font=FONTS["small"], text_color=COLORS["text_dim"]).pack(side="left", padx=(8, 0))

        hdr_right = ctk.CTkFrame(hdr_frame, fg_color="transparent")
        hdr_right.pack(side="right")

        self.lbl_todo_badge = ctk.CTkLabel(hdr_right, text="3 TASKS FOCUS",
                                           font=("Segoe UI", 9, "bold"),
                                           text_color="#1D4ED8", fg_color="#DBEAFE",
                                           corner_radius=4, width=95, height=22)
        self.lbl_todo_badge.pack(side="right")

        # Cards Row: 3 side-by-side responsive slots
        self.todo_cards_frame = ctk.CTkFrame(self.todo_outer, fg_color="transparent")
        self.todo_cards_frame.pack(fill="x")
        for c in range(3):
            self.todo_cards_frame.grid_columnconfigure(c, weight=1, uniform="todo_col")

        self._todo_slots = []
        for slot_idx in range(3):
            slot = self._create_todo_slot_widget(slot_idx)
            self._todo_slots.append(slot)

    def _create_todo_slot_widget(self, slot_idx):
        """Constructs widget layout for a single TO-DO slot card."""
        card = ctk.CTkFrame(self.todo_cards_frame, fg_color=COLORS["card_bg"],
                            corner_radius=10, border_width=1, border_color=COLORS["border"])
        card.grid(row=0, column=slot_idx, sticky="nsew", padx=6, pady=2)

        # Blue accent top edge (matching KPI style)
        top_edge = ctk.CTkFrame(card, fg_color=COLORS["accent"], height=4, corner_radius=2)
        top_edge.pack(fill="x", side="top", padx=0, pady=0)
        top_edge.pack_propagate(False)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # Top row: Rank badge + ID on left, Priority + Due date on right
        top_row = ctk.CTkFrame(body, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 4))

        left_meta = ctk.CTkFrame(top_row, fg_color="transparent")
        left_meta.pack(side="left")

        lbl_rank = ctk.CTkLabel(left_meta, text=f"#{slot_idx + 1} PRIORITY",
                                font=("Segoe UI", 9, "bold"),
                                text_color="#1D4ED8", fg_color="#EFF6FF",
                                corner_radius=4, width=76, height=20)
        lbl_rank.pack(side="left", padx=(0, 6))

        lbl_id = ctk.CTkLabel(left_meta, text="", font=FONTS["small"], text_color=COLORS["text_dim"])
        lbl_id.pack(side="left")

        right_meta = ctk.CTkFrame(top_row, fg_color="transparent")
        right_meta.pack(side="right")

        lbl_prio = ctk.CTkLabel(right_meta, text="", font=("Segoe UI", 9, "bold"),
                                text_color=COLORS["text_dim"])
        lbl_prio.pack(side="left", padx=(0, 6))

        lbl_dl = ctk.CTkLabel(right_meta, text="", font=FONTS["small"], text_color=COLORS["text_dim"])
        lbl_dl.pack(side="left")

        # Middle: Description
        lbl_desc = ctk.CTkLabel(body, text="Loading task...", font=("Segoe UI", 12, "bold"),
                                text_color=COLORS["text_main"], justify="left", anchor="nw", wraplength=280)
        lbl_desc.pack(fill="x", anchor="w", pady=(2, 2))

        # Checklist info / meta
        lbl_meta = ctk.CTkLabel(body, text="", font=FONTS["small"], text_color=COLORS["text_dim"], anchor="w")
        lbl_meta.pack(fill="x", anchor="w", pady=(0, 6))

        # Bottom: Actions frame with separate dedicated 1-click outline buttons: Checklist, Delay, View
        actions_row = ctk.CTkFrame(body, fg_color="transparent")
        actions_row.pack(fill="x", pady=(4, 0))

        btn_checklist = ctk.CTkButton(
            actions_row, text="☑ Checklist", width=84, height=30,
            font=FONTS["small"], corner_radius=6,
            fg_color="transparent", border_width=1,
            border_color=COLORS["accent"], text_color=COLORS["accent"],
            hover_color="#EFF6FF"
        )
        btn_checklist.pack(side="left", padx=(0, 6))

        btn_update = ctk.CTkButton(
            actions_row, text="Update", width=62, height=30,
            font=FONTS["small"], corner_radius=6,
            fg_color="transparent", border_width=1,
            border_color=COLORS["accent"], text_color=COLORS["accent"],
            hover_color="#EFF6FF"
        )
        btn_update.pack(side="left", padx=(0, 6))

        btn_delayed = ctk.CTkButton(
            actions_row, text="⏰ Delay", width=70, height=30,
            font=FONTS["small"], corner_radius=6,
            fg_color="transparent", border_width=1,
            border_color="#F59E0B", text_color="#D97706",
            hover_color="#FFFBEB"
        )
        btn_delayed.pack(side="left", padx=(0, 6))

        btn_view = ctk.CTkButton(
            actions_row, text="View", width=55, height=30,
            font=FONTS["small"], corner_radius=6,
            fg_color="transparent", border_width=1,
            border_color=COLORS["border"], text_color=COLORS["text_main"],
            hover_color=COLORS["bg"]
        )
        btn_view.pack(side="left")

        # Dynamic wraplength on resize
        def on_body_configure(event, l_desc=lbl_desc):
            try:
                new_w = max(180, event.width - 8)
                l_desc.configure(wraplength=new_w)
            except Exception:
                pass
        body.bind("<Configure>", on_body_configure)

        return {
            "slot_idx": slot_idx,
            "card": card,
            "top_edge": top_edge,
            "body": body,
            "lbl_rank": lbl_rank,
            "lbl_id": lbl_id,
            "lbl_prio": lbl_prio,
            "lbl_dl": lbl_dl,
            "lbl_desc": lbl_desc,
            "lbl_meta": lbl_meta,
            "actions_row": actions_row,
            "btn_checklist": btn_checklist,
            "btn_update": btn_update,
            "btn_delayed": btn_delayed,
            "btn_view": btn_view,
            "current_task": None,
            "is_animating": False,
        }

    def _get_prioritized_todo_tasks(self, all_tasks, today):
        """Returns incomplete tasks sorted by industrial SLA standards (SLA breach > urgency > priority > age)."""
        active_tasks = [t for t in all_tasks if str(getattr(t, "status", "")).strip().lower() not in ("completed", "done")]

        prio_order = {"urgent": 0, "high": 1, "medium": 2, "normal": 2, "low": 3}
        far_future = datetime(2099, 12, 31).date()

        def score_task(t):
            prio = prio_order.get(str(getattr(t, "priority", "")).strip().lower(), 2)
            d = getattr(t, "_effective_deadline_date", None)
            assigned = _parse_deadline(getattr(t, "date", "")) or far_future

            if d is not None:
                if d < today:
                    # Tier 0: Overdue (SLA breach). Sort by priority first, then longest overdue first
                    overdue_days = (today - d).days
                    return (0, prio, -overdue_days)
                elif d == today:
                    # Tier 1: Due Today (imminent SLA risk)
                    return (1, prio, 0)
                else:
                    # Tier 2: Future deadlines. Earliest deadline date first, then priority
                    return (2, (d - today).days, prio)
            else:
                # Tier 3: No deadline specified. Priority first, then oldest assigned date
                return (3, prio, (assigned - datetime(1970, 1, 1).date()).days)

        active_tasks.sort(key=score_task)
        return active_tasks

    def _update_todo_section(self, all_tasks, today):
        """Updates the top 3 TO-DO slots from active tasks using industrial SLA scoring."""
        active_tasks = self._get_prioritized_todo_tasks(all_tasks, today)

        # Update header badge
        num_active = len(active_tasks)
        if num_active >= 3:
            self.lbl_todo_badge.configure(text="3 TASKS FOCUS", text_color="#1D4ED8", fg_color="#DBEAFE")
        elif num_active == 2:
            self.lbl_todo_badge.configure(text="2 TASKS FOCUS", text_color="#1D4ED8", fg_color="#DBEAFE")
        elif num_active == 1:
            self.lbl_todo_badge.configure(text="1 TASK FOCUS", text_color="#1D4ED8", fg_color="#DBEAFE")
        else:
            self.lbl_todo_badge.configure(text="0 TASKS PENDING", text_color="#15803D", fg_color="#DCFCE7")

        for idx in range(3):
            slot = self._todo_slots[idx]
            if slot.get("is_animating"):
                continue

            old_task = slot.get("current_task")
            if idx < len(active_tasks):
                task = active_tasks[idx]
                is_changed = (old_task is None or old_task.task_id != task.task_id) and not self._is_initial_load
                self._populate_todo_slot(idx, task, idx + 1, today, is_new=is_changed)
            else:
                self._set_todo_slot_empty(idx, idx + 1)

    def _populate_todo_slot(self, slot_idx, task, rank_num, today, is_new=False):
        """Populates a slot with task details and binds all interactive controls."""
        slot = self._todo_slots[slot_idx]
        slot["current_task"] = task
        card = slot["card"]
        top_edge = slot["top_edge"]

        # Double click to view full details
        def on_double_click(event=None, tk=task):
            self.show_task_details_dialog(tk)

        for w in (card, slot["body"], slot["lbl_desc"], slot["lbl_meta"], slot["lbl_id"]):
            w.bind("<Double-1>", on_double_click)

        # Rank pill badge
        rank_colors = [
            ("#1D4ED8", "#EFF6FF", "#1 PRIORITY"),
            ("#2563EB", "#F1F5F9", "#2 PRIORITY"),
            ("#475569", "#F8FAFC", "#3 PRIORITY"),
        ]
        rc = rank_colors[min(slot_idx, len(rank_colors) - 1)]
        slot["lbl_rank"].configure(text=rc[2], text_color=rc[0], fg_color=rc[1])

        # Task ID
        short_id = str(task.task_id)[-4:] if getattr(task, 'task_id', None) else ""
        slot["lbl_id"].configure(text=f"[#{short_id}]" if short_id else "")

        # Priority
        prio_str = str(task.priority).strip().upper()
        prio_color = COLORS["error"] if task.priority.lower() in ("high", "urgent") else (
            COLORS["warning"] if task.priority.lower() in ("medium", "normal") else COLORS["text_dim"]
        )
        slot["lbl_prio"].configure(text=prio_str, text_color=prio_color)

        # Due Date / Overdue badge
        eff_dl = getattr(task, "_effective_deadline", task.deadline)
        dl_str = format_date(eff_dl)
        dl_date = getattr(task, "_effective_deadline_date", None)
        if dl_date and dl_date < today and task.status.lower() not in ("completed", "done"):
            overdue_days = (today - dl_date).days
            slot["lbl_dl"].configure(text=f"⚠ Overdue ({overdue_days}d)", text_color=COLORS["error"], font=("Segoe UI", 9, "bold"))
        elif dl_date and dl_date == today:
            slot["lbl_dl"].configure(text="⏰ Due Today", text_color="#D97706", font=("Segoe UI", 9, "bold"))
        else:
            slot["lbl_dl"].configure(text=f"Due: {dl_str}", text_color=COLORS["text_dim"], font=FONTS["small"])

        # Description (compact display to ensure uniform height)
        desc_text = str(getattr(task, "description", "") or getattr(task, "task", "") or "")
        short_desc = desc_text if len(desc_text) <= 110 else desc_text[:107] + "..."
        slot["lbl_desc"].configure(text=short_desc, text_color=COLORS["text_main"])

        # Checklist or subtext
        has_checklist = bool(getattr(task, 'checklist', None))
        if has_checklist:
            total_items = len(task.checklist)
            done_items = sum(
                1 for item in task.checklist
                if (isinstance(item, dict) and item.get("completed")) or
                   (isinstance(item, str) and item.startswith("[x]"))
            )
            slot["lbl_meta"].configure(text=f"☑ Checklist: {done_items}/{total_items} completed",
                                       text_color=COLORS["accent"] if done_items < total_items else COLORS["success"])
        else:
            assigned_by = getattr(task, "assigned_by", "")
            slot["lbl_meta"].configure(text=f"Assigned by: {assigned_by}" if assigned_by else "",
                                       text_color=COLORS["text_dim"])

        # Ensure actions row is visible
        slot["actions_row"].pack(fill="x", pady=(4, 0))

        # Checklist button
        if has_checklist:
            slot["btn_checklist"].pack(side="left", padx=(0, 4), before=slot["btn_update"])
            slot["btn_checklist"].configure(state="normal", text="☑ Checklist",
                                            command=lambda t=task: self.show_task_details_dialog(t, checklist_only=True))
        else:
            slot["btn_checklist"].pack_forget()

        slot["btn_update"].pack(side="left", padx=(0, 4), before=slot["btn_delayed"])
        slot["btn_update"].configure(state="normal", text="Update",
                                     command=lambda t=task: self.prompt_task_text_update(t))

        slot["btn_delayed"].configure(state="normal", text="⏰ Delay",
                                      command=lambda t=task: self.prompt_extension_request(t, None))

        slot["btn_view"].configure(state="normal", text="View",
                                   command=lambda t=task: self.show_task_details_dialog(t))

        # If newly arrived, run entrance animation
        if is_new:
            self._animate_todo_card_entrance(card, top_edge)
        else:
            card.configure(fg_color=COLORS["card_bg"], border_color=COLORS["border"], border_width=1)
            top_edge.configure(fg_color=COLORS["accent"])

    def _set_todo_slot_empty(self, slot_idx, rank_num):
        """Sets a slot to clean placeholder state when no task is pending."""
        slot = self._todo_slots[slot_idx]
        slot["current_task"] = None
        card = slot["card"]
        top_edge = slot["top_edge"]

        top_edge.configure(fg_color="#CBD5E1")
        slot["lbl_rank"].configure(text=f"#{rank_num} CLEAR", text_color="#94A3B8", fg_color="#F1F5F9")
        slot["lbl_id"].configure(text="")
        slot["lbl_prio"].configure(text="")
        slot["lbl_dl"].configure(text="")
        slot["lbl_desc"].configure(text="All caught up!", text_color=COLORS["text_dim"])
        slot["lbl_meta"].configure(text="No pending task in this slot", text_color="#94A3B8")
        slot["actions_row"].pack_forget()
        card.configure(fg_color=COLORS["card_bg"], border_color=COLORS["border"], border_width=1)

    def _handle_todo_complete(self, slot_idx, task):
        """Direct 1-click completion for TO-DO card slot."""
        if getattr(task, 'checklist', None):
            all_completed = True
            for item in task.checklist:
                if isinstance(item, dict) and not item.get("completed"):
                    all_completed = False
                elif isinstance(item, str) and not item.startswith("[x]"):
                    all_completed = False
            if not all_completed:
                messagebox.showwarning("Incomplete Checklist",
                                       "You cannot mark this task as complete until all checklist items are ticked.\n"
                                       "Click '☑ List' to review and complete checklist items.")
                return

        self._animate_todo_completion_and_replace(slot_idx, task)

    def _animate_todo_completion_and_replace(self, slot_idx, task):
        """Animates task completion with an emerald flash and smoothly replaces it with the next prioritized task."""
        slot = self._todo_slots[slot_idx]
        slot["is_animating"] = True
        card = slot["card"]
        top_edge = slot["top_edge"]
        btn_delayed = slot.get("btn_delayed")
        btn_checklist = slot.get("btn_checklist")
        btn_view = slot.get("btn_view")

        # Step 1: Green completion highlight & disable controls
        if btn_delayed and btn_delayed.winfo_exists(): btn_delayed.configure(state="disabled")
        if btn_checklist and btn_checklist.winfo_exists(): btn_checklist.configure(state="disabled")
        if btn_view and btn_view.winfo_exists(): btn_view.configure(state="disabled")
        card.configure(border_color="#16A34A", border_width=2)
        top_edge.configure(fg_color="#16A34A")
        slot["lbl_rank"].configure(text="✓ COMPLETED", text_color="#15803D", fg_color="#BBF7D0")

        # Step 2: Trigger inline update backend sync with non-blocking modal
        self.do_inline_update(task, "Completed", btn_view, skip_modal=True)

        # Step 3: After a 280ms celebration pause, replace card with the next task smoothly
        def do_replace():
            today = datetime.now().date()
            active_tasks = self._get_prioritized_todo_tasks(self.current_tasks, today)

            for i in range(3):
                s = self._todo_slots[i]
                old_t = s.get("current_task")
                if i < len(active_tasks):
                    new_t = active_tasks[i]
                    is_changed = (old_t is None or old_t.task_id != new_t.task_id or i == slot_idx)
                    self._populate_todo_slot(i, new_t, i + 1, today, is_new=is_changed)
                else:
                    self._set_todo_slot_empty(i, i + 1)

            slot["is_animating"] = False

            # Update KPI labels for active & completed
            active_cnt = len([t for t in self.current_tasks if t.status.lower() not in ("completed", "done")])
            comp_cnt = len([t for t in self.current_tasks if t.status.lower() in ("completed", "done")])
            if "active" in self.kpi_labels and self.kpi_labels["active"].winfo_exists():
                self.kpi_labels["active"].configure(text=str(active_cnt))
            if "completed" in self.kpi_labels and self.kpi_labels["completed"].winfo_exists():
                self.kpi_labels["completed"].configure(text=str(comp_cnt))

        self.after(280, do_replace)

    def _animate_todo_card_entrance(self, card, top_edge):
        """Animates a TO-DO card with a luminous blue highlight fade and smooth quadratic easing."""
        start_bg = "#EFF6FF"
        start_border = "#3B82F6"
        end_bg = COLORS["card_bg"]
        end_border = COLORS["border"]

        card.configure(fg_color=start_bg, border_color=start_border, border_width=2)
        top_edge.configure(fg_color=COLORS["accent"])

        def step_color(step=0, total_steps=16):
            if not card.winfo_exists():
                return
            factor = step / total_steps
            eased = 1 - (1 - factor) ** 2  # smooth ease-out
            bg = _interpolate_color(start_bg, end_bg, eased)
            border = _interpolate_color(start_border, end_border, eased)
            try:
                card.configure(fg_color=bg, border_color=border)
            except Exception:
                pass
            if step < total_steps:
                self.after(30, lambda: step_color(step + 1, total_steps))
            else:
                try:
                    card.configure(fg_color=end_bg, border_color=end_border, border_width=1)
                except Exception:
                    pass

        self.after(40, step_color)

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
                        fg_color="transparent",
                        text_color=COLORS["accent"],
                        hover_color="#EFF6FF",
                        border_width=1.5,
                        border_color=COLORS["accent"],
                        font=(FONTS["small"][0], FONTS["small"][1], "bold")
                    )
                else:
                    btn.configure(
                        text=f"{param_label} ↕",
                        fg_color="transparent",
                        text_color=COLORS["text_dim"],
                        hover_color="#F1F5F9",
                        border_width=1,
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

        user_interacting = False

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
        """Updates text, badges, and action buttons on an existing task card in-place."""
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

        # Update action buttons state
        is_done = task.status.lower() in ("completed", "done")
        has_checklist = bool(getattr(task, 'checklist', None))

        btn_delayed = info.get("btn_delayed")
        if btn_delayed and btn_delayed.winfo_exists():
            if is_done:
                btn_delayed.pack_forget()
            else:
                if not btn_delayed.winfo_ismapped():
                    btn_delayed.pack(side="left", padx=(0, 6), before=info.get("btn_view"))
                btn_delayed.configure(state="normal")

        btn_update = info.get("btn_update")
        if btn_update and btn_update.winfo_exists():
            if is_done:
                btn_update.pack_forget()
            else:
                if not btn_update.winfo_ismapped():
                    before_w = btn_delayed if (btn_delayed and btn_delayed.winfo_ismapped()) else info.get("btn_view")
                    btn_update.pack(side="left", padx=(0, 6), before=before_w)
                btn_update.configure(state="normal")

        btn_checklist = info.get("btn_checklist")
        if btn_checklist and btn_checklist.winfo_exists():
            if has_checklist:
                if not btn_checklist.winfo_ismapped():
                    before_w = btn_update if (btn_update and btn_update.winfo_ismapped()) else (btn_delayed if (btn_delayed and btn_delayed.winfo_ismapped()) else info.get("btn_view"))
                    btn_checklist.pack(side="left", padx=(0, 6), before=before_w)
                btn_checklist.configure(state="normal")
            else:
                btn_checklist.pack_forget()

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
        actions_frame.grid(row=0, column=3, padx=(10, 20), pady=14, sticky="e")

        has_checklist = bool(getattr(task, 'checklist', None))
        is_done = task.status.lower() in ("completed", "done")

        btn_checklist = ctk.CTkButton(
            actions_frame, text="☑ Checklist", width=92, height=32,
            font=FONTS["small"], corner_radius=6,
            fg_color="transparent", border_width=1,
            border_color=COLORS["accent"], text_color=COLORS["accent"],
            hover_color="#EFF6FF",
            command=lambda t=task: self.show_task_details_dialog(t, checklist_only=True)
        )
        if has_checklist:
            btn_checklist.pack(side="left", padx=(0, 6))

        btn_update = ctk.CTkButton(
            actions_frame, text="Update", width=76, height=32,
            font=FONTS["small"], corner_radius=6,
            fg_color="transparent", border_width=1,
            border_color=COLORS["accent"], text_color=COLORS["accent"],
            hover_color="#EFF6FF",
            command=lambda t=task: self.prompt_task_text_update(t)
        )
        if not is_done:
            btn_update.pack(side="left", padx=(0, 6))

        btn_delayed = ctk.CTkButton(
            actions_frame, text="⏰ Delay", width=76, height=32,
            font=FONTS["small"], corner_radius=6,
            fg_color="transparent", border_width=1,
            border_color="#F59E0B", text_color="#D97706",
            hover_color="#FFFBEB",
            command=lambda t=task: self.prompt_extension_request(t, None)
        )
        if not is_done:
            btn_delayed.pack(side="left", padx=(0, 6))

        btn_view = ctk.CTkButton(
            actions_frame, text="View", width=55, height=32, font=FONTS["small"], corner_radius=6,
            fg_color="transparent", border_width=1, border_color=COLORS["border"],
            text_color=COLORS["text_main"], hover_color=COLORS["bg"],
            command=lambda t=task: self.show_task_details_dialog(t)
        )
        btn_view.pack(side="left")

        row_info = {
            "row_widget": row,
            "inner_card": inner,
            "task": task,
            "btn_checklist": btn_checklist,
            "btn_update": btn_update,
            "btn_delayed": btn_delayed,
            "btn_view": btn_view,
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


    def prompt_task_text_update(self, task):
        """Opens dedicated modern modal dialog for updating progress and evaluating against checklist."""
        dialog = ctk.CTkToplevel(self)
        dialog.attributes("-alpha", 0.0)
        dialog.title(f"Update Task Progress: {task.task_id}")
        dialog.geometry("900x560")
        dialog.configure(fg_color="#F8FAFC")
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = max(20, self.winfo_rootx() + (self.winfo_width() // 2) - (900 // 2))
        y = max(20, self.winfo_rooty() + (self.winfo_height() // 2) - (560 // 2))
        dialog.geometry(f"+{x}+{y}")
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        fade_in(dialog)

        # ── Header ──
        hdr = ctk.CTkFrame(dialog, fg_color="#FFFFFF", corner_radius=0, border_width=0)
        hdr.pack(fill="x")
        
        top_accent = ctk.CTkFrame(hdr, fg_color=COLORS["accent"], height=3)
        top_accent.pack(fill="x")

        hdr_content = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_content.pack(fill="x", padx=24, pady=14)

        # Badges row: Task ID + Priority + Deadline
        badge_row = ctk.CTkFrame(hdr_content, fg_color="transparent")
        badge_row.pack(fill="x", pady=(0, 4))

        short_id = str(task.task_id)[-4:] if getattr(task, 'task_id', None) else ""
        if short_id:
            ctk.CTkLabel(badge_row, text=f"#{short_id}", font=("Segoe UI", 10, "bold"),
                         text_color="#1D4ED8", fg_color="#EFF6FF", corner_radius=6,
                         height=24, width=54).pack(side="left", padx=(0, 8))

        prio_color = COLORS["error"] if task.priority.lower() in ("high", "urgent") else (
            COLORS["warning"] if task.priority.lower() in ("medium", "normal") else COLORS["text_dim"]
        )
        ctk.CTkLabel(badge_row, text=task.priority.upper(), font=("Segoe UI", 9, "bold"),
                     text_color=prio_color, fg_color="#F1F5F9", corner_radius=6,
                     height=24, padx=8).pack(side="left", padx=(0, 8))

        eff_dl = getattr(task, "_effective_deadline", task.deadline)
        dl_str = format_date(eff_dl)
        ctk.CTkLabel(badge_row, text=f"⏰ Due: {dl_str}", font=FONTS["small"],
                     text_color=COLORS["text_dim"]).pack(side="left")

        # Task Description
        ctk.CTkLabel(hdr_content, text=task.description, font=("Segoe UI", 13, "bold"),
                     text_color=COLORS["text_main"], wraplength=840, justify="left").pack(anchor="w", pady=(2, 0))

        # ── Checklist Data Parsing ──
        pending_milestones = []
        completed_milestones = []
        if getattr(task, 'checklist', None):
            for idx, it in enumerate(task.checklist):
                is_done = False
                t_str = str(it)
                if isinstance(it, dict):
                    is_done = it.get("completed", False)
                    t_str = it.get("text", "") or it.get("step", "") or it.get("goal", "")
                elif isinstance(it, str):
                    is_done = it.startswith("[x]")
                    if is_done or it.startswith("[ ]"):
                        t_str = it[3:].strip()
                t_str = t_str.strip()
                if not t_str:
                    continue
                if is_done:
                    completed_milestones.append((idx, t_str))
                else:
                    pending_milestones.append((idx, t_str))

        total_cnt = len(pending_milestones) + len(completed_milestones)

        # ── Main Side-by-Side 2-Column Content ──
        content_grid = ctk.CTkFrame(dialog, fg_color="transparent")
        content_grid.pack(fill="both", expand=True, padx=22, pady=(12, 10))
        content_grid.grid_columnconfigure(0, weight=1, uniform="modal_cols")
        content_grid.grid_columnconfigure(1, weight=1, uniform="modal_cols")
        content_grid.grid_rowconfigure(0, weight=1)

        # ── LEFT COLUMN: Remaining Milestones (Checklist) ──
        col_left = ctk.CTkFrame(content_grid, fg_color="#FFFFFF", corner_radius=10,
                                border_width=1, border_color="#E2E8F0")
        col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        chk_hdr = ctk.CTkFrame(col_left, fg_color="transparent")
        chk_hdr.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(chk_hdr, text="Remaining Milestones", font=("Segoe UI", 12, "bold"),
                     text_color=COLORS["text_main"]).pack(side="left")

        if total_cnt > 0:
            if pending_milestones:
                pill_text = f"{len(pending_milestones)} of {total_cnt} Remaining"
                pill_fg = "#EFF6FF"
                pill_tc = "#1D4ED8"
            else:
                pill_text = "✓ All Completed"
                pill_fg = "#DCFCE7"
                pill_tc = "#15803D"
            ctk.CTkLabel(chk_hdr, text=pill_text, font=("Segoe UI", 9, "bold"),
                         fg_color=pill_fg, text_color=pill_tc, corner_radius=6,
                         height=22, padx=8).pack(side="right")

            progress_val = len(completed_milestones) / total_cnt
            pbar = ctk.CTkProgressBar(col_left, height=4, corner_radius=2,
                                      fg_color="#F1F5F9", progress_color=COLORS["accent"])
            pbar.pack(fill="x", padx=16, pady=(0, 6))
            pbar.set(progress_val)

        ctk.CTkLabel(
            col_left, text="AI evaluates your update against these pending steps:",
            font=FONTS["small"], text_color=COLORS["text_dim"]
        ).pack(anchor="w", padx=16, pady=(0, 6))

        # Scrollable container for remaining items
        scroll_chk = ctk.CTkScrollableFrame(col_left, fg_color="transparent")
        scroll_chk.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        if pending_milestones:
            for step_num, (orig_idx, m_text) in enumerate(pending_milestones, 1):
                tile = ctk.CTkFrame(scroll_chk, fg_color="#F8FAFC", corner_radius=8,
                                    border_width=1, border_color="#E2E8F0")
                tile.pack(fill="x", pady=4, padx=4)

                # Step index circle on the left
                ctk.CTkLabel(
                    tile, text=f"{step_num}", width=22, height=22,
                    corner_radius=11, fg_color="#E2E8F0",
                    text_color="#475569", font=("Segoe UI", 10, "bold")
                ).pack(side="left", padx=(10, 8), pady=8)

                # Status pill packed on the right FIRST so it NEVER gets cut off
                ctk.CTkLabel(
                    tile, text="Pending", font=("Segoe UI", 9, "bold"),
                    fg_color="#FEF3C7", text_color="#B45309", corner_radius=4,
                    width=56, height=20
                ).pack(side="right", padx=(6, 10), pady=8)

                # Milestone description in the middle with clean wrapping
                ctk.CTkLabel(
                    tile, text=m_text, font=("Segoe UI", 10),
                    text_color=COLORS["text_main"], justify="left",
                    wraplength=230, anchor="w"
                ).pack(side="left", fill="x", expand=True, padx=(0, 6), pady=8)
        else:
            if total_cnt > 0:
                ctk.CTkLabel(
                    scroll_chk, text="🎉 All checklist milestones are already completed!\nYou can still submit an update.",
                    font=FONTS["small"], text_color="#15803D", justify="left", wraplength=340
                ).pack(anchor="w", padx=16, pady=20)
            else:
                ctk.CTkLabel(
                    scroll_chk, text="ℹ No checklist milestones attached to this task.\nYour update will still be recorded.",
                    font=FONTS["small"], text_color=COLORS["text_dim"], justify="left", wraplength=340
                ).pack(anchor="w", padx=16, pady=20)

        # ── RIGHT COLUMN: Describe Your Progress (Text Box) ──
        col_right = ctk.CTkFrame(content_grid, fg_color="#FFFFFF", corner_radius=10,
                                 border_width=1, border_color="#E2E8F0")
        col_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(col_right, text="What did you do on this task?", font=("Segoe UI", 12, "bold"),
                     text_color=COLORS["text_main"]).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(col_right, text="In your own words, describe your progress. AI will evaluate and tick off matching checklist milestones.",
                     font=FONTS["small"], text_color=COLORS["text_dim"], wraplength=370, justify="left").pack(anchor="w", padx=16, pady=(0, 8))

        txt = ctk.CTkTextbox(col_right, corner_radius=8,
                             border_width=1.5, border_color="#CBD5E1", fg_color="#FFFFFF",
                             font=("Segoe UI", 11), wrap="word")
        txt.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        txt.focus_set()

        ctk.CTkLabel(col_right, text="💡 Tip: You can describe multiple completed milestones at once.",
                     font=("Segoe UI", 9), text_color=COLORS["text_dim"]).pack(anchor="w", padx=16, pady=(0, 12))

        # ── Bottom Action Bar ──
        btm_bar = ctk.CTkFrame(dialog, fg_color="#FFFFFF", height=56, border_width=1, border_color="#E2E8F0")
        btm_bar.pack(fill="x", side="bottom")

        inner_bar = ctk.CTkFrame(btm_bar, fg_color="transparent")
        inner_bar.pack(fill="both", expand=True, padx=22, pady=10)

        btn_submit = ctk.CTkButton(
            inner_bar, text="Submit Progress", height=36, width=140,
            corner_radius=8, font=("Segoe UI", 11, "bold"),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"]
        )
        btn_submit.pack(side="left", padx=(0, 10))

        btn_cancel = ctk.CTkButton(
            inner_bar, text="Cancel", height=36, width=80,
            corner_radius=8, font=FONTS["small"],
            fg_color="transparent", border_width=1, border_color=COLORS["border"],
            text_color=COLORS["text_dim"], hover_color=COLORS["bg"],
            command=dialog.destroy
        )
        btn_cancel.pack(side="left", padx=(0, 10))

        lbl_status = ctk.CTkLabel(inner_bar, text="", font=("Segoe UI", 10), text_color=COLORS["text_dim"])
        lbl_status.pack(side="left")

        ctk.CTkLabel(inner_bar, text="Press Ctrl+Enter to submit", font=("Segoe UI", 9),
                     text_color=COLORS["text_dim"]).pack(side="right")

        def on_sub():
            self._handle_task_text_update(task, txt, btn_submit, btn_cancel, lbl_status, dialog)

        btn_submit.configure(command=on_sub)
        txt.bind("<Control-Return>", lambda e: on_sub())

    def _handle_task_text_update(self, task, txt_widget, btn_submit, btn_cancel, lbl_status, panel_or_dialog=None, btn_toggle=None):
        """Submits progress text to n8n AI workflow, updates checklist milestones, and refreshes UI."""
        text_val = txt_widget.get("1.0", "end").strip()
        if not text_val:
            messagebox.showwarning("Empty Update", "Please describe what you worked on or completed for this task.")
            return

        btn_submit.configure(state="disabled", text="Interpreting...")
        if btn_cancel:
            btn_cancel.configure(state="disabled")
        txt_widget.configure(state="disabled")
        lbl_status.configure(text="🤖 Interpreting with AI against checklist...", text_color=COLORS["accent"])

        def worker():
            try:
                resp = self.n8n_client.submit_task_progress_update(
                    task_id=task.task_id,
                    update_text=text_val,
                    current_checklist=task.checklist,
                    task_description=task.description,
                    employee_name=getattr(self, "current_user", "") or task.assigned_to,
                    current_status=task.status
                )
                self.after(0, lambda: on_success(resp))
            except Exception as e:
                self.after(0, lambda: on_error(e))

        def on_success(resp):
            try:
                new_checklist = resp.get("checklist")
                new_status = resp.get("status")
                all_completed = resp.get("all_completed", False)
                explanation = resp.get("explanation", "")
                newly_completed = resp.get("newly_completed_steps", [])

                if new_checklist:
                    task.checklist = new_checklist
                if new_status:
                    task.status = new_status

                # Dual sync: Ensure Supabase has the latest checklist and status
                threading.Thread(
                    target=lambda: self.sheets_client.update_task_checklist(
                        task.task_id, task.checklist,
                        status=task.status if all_completed else None,
                        updated_by="UI Progress Update"
                    ),
                    daemon=True
                ).start()

                # Record optimistic local update
                record_task_update(task.task_id, {
                    "Status": task.status,
                    "Checklist": task.checklist,
                    "Updated By": "UI Progress Update",
                    "Last Updated": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                })

                # Clear and reset text box
                try:
                    txt_widget.configure(state="normal")
                    txt_widget.delete("1.0", "end")
                    btn_submit.configure(state="normal", text="Submit Update")
                    if btn_cancel:
                        btn_cancel.configure(state="normal")
                except Exception:
                    pass

                # Close panel or dialog
                if panel_or_dialog:
                    if hasattr(panel_or_dialog, "destroy"):
                        panel_or_dialog.destroy()
                    elif hasattr(panel_or_dialog, "grid_remove"):
                        panel_or_dialog.grid_remove()
                if btn_toggle:
                    btn_toggle.configure(text="Update", fg_color="transparent")

                self._full_refresh()

                # Feedback toast/messagebox
                msg = f"Task {task.task_id} updated successfully!\n\n"
                if newly_completed:
                    msg += "Milestones checked off:\n• " + "\n• ".join(newly_completed) + "\n\n"
                if all_completed:
                    msg += "🎉 All checklist milestones are now completed! Task marked as Completed.\n\n"
                if explanation:
                    msg += f"AI Summary: {explanation}"

                messagebox.showinfo("Update Processed", msg)
            except Exception as ex:
                on_error(ex)

        def on_error(err):
            try:
                btn_submit.configure(state="normal", text="Submit Update")
                if btn_cancel:
                    btn_cancel.configure(state="normal")
                txt_widget.configure(state="normal")
                lbl_status.configure(text=f"Failed: {str(err)[:50]}", text_color=COLORS["error"])
            except Exception:
                pass
            messagebox.showerror("Update Error", f"Failed to process update via n8n:\n{err}")

        threading.Thread(target=worker, daemon=True).start()

    # ── Task Detail Dialog ───────────────────────────────────────────────

    def show_task_details_dialog(self, task, checklist_only=False):
        dialog = ctk.CTkToplevel(self)
        dialog.attributes("-alpha", 0.0)
        dialog.title("Checklist Milestones" if checklist_only else f"Task Details: {task.task_id}")
        dialog.geometry("740x670")
        dialog.configure(fg_color="#F8FAFC")
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (740 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (670 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        fade_in(dialog)

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=22, pady=(20, 10))

        eff_dl = getattr(task, "_effective_deadline", task.deadline)
        is_ext = getattr(task, "_is_extended", False)
        today = datetime.now().date()
        dl_date = getattr(task, "_effective_deadline_date", None)
        is_done = task.status.lower() in ("completed", "done")
        is_overdue = dl_date and dl_date < today and not is_done

        # ── 1. Header Card (Title, ID, Badges) ──
        hdr_card = ctk.CTkFrame(scroll, fg_color="#FFFFFF", corner_radius=12,
                                border_width=1, border_color=COLORS["border"])
        hdr_card.pack(fill="x", pady=(0, 14))

        hdr_top = ctk.CTkFrame(hdr_card, fg_color="transparent")
        hdr_top.pack(fill="x", padx=18, pady=(16, 8))

        # Left Badges: ID + Priority + Status
        badges_left = ctk.CTkFrame(hdr_top, fg_color="transparent")
        badges_left.pack(side="left")

        short_id = str(task.task_id)[-4:] if getattr(task, 'task_id', None) else ""
        if short_id:
            ctk.CTkLabel(badges_left, text=f"#{short_id}", font=("Segoe UI", 10, "bold"),
                         text_color="#1D4ED8", fg_color="#EFF6FF", corner_radius=6,
                         height=24, width=54).pack(side="left", padx=(0, 8))

        # Status Badge
        st_color = ("#15803D", "#DCFCE7") if is_done else (
            ("#B91C1C", "#FEE2E2") if is_overdue else ("#1D4ED8", "#DBEAFE")
        )
        ctk.CTkLabel(badges_left, text=task.status.upper(), font=("Segoe UI", 10, "bold"),
                     text_color=st_color[0], fg_color=st_color[1], corner_radius=6,
                     height=24, padx=10).pack(side="left", padx=(0, 8))

        # Priority Badge
        prio_lower = str(task.priority).strip().lower()
        prio_color = ("#DC2626", "#FEF2F2") if prio_lower in ("high", "urgent") else (
            ("#D97706", "#FFFBEB") if prio_lower in ("medium", "normal") else ("#475569", "#F1F5F9")
        )
        ctk.CTkLabel(badges_left, text=f"● {task.priority.upper()}", font=("Segoe UI", 10, "bold"),
                     text_color=prio_color[0], fg_color=prio_color[1], corner_radius=6,
                     height=24, padx=10).pack(side="left")

        # Right Badge: Due Date
        due_text = f"⚠ Overdue: {format_date(eff_dl)}" if is_overdue else f"Due: {format_date(eff_dl)}"
        due_bg = "#FEF2F2" if is_overdue else "#F8FAFC"
        due_fg = "#DC2626" if is_overdue else COLORS["text_dim"]
        ctk.CTkLabel(hdr_top, text=due_text, font=("Segoe UI", 10, "bold"),
                     text_color=due_fg, fg_color=due_bg, corner_radius=6,
                     height=24, padx=10).pack(side="right")

        # Description text
        desc_frame = ctk.CTkFrame(hdr_card, fg_color="transparent")
        desc_frame.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkLabel(desc_frame, text="DESCRIPTION", font=("Segoe UI", 9, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(desc_frame, text=str(task.description or "No description provided"),
                     font=("Segoe UI", 13), text_color=COLORS["text_main"],
                     justify="left", anchor="w", wraplength=660).pack(anchor="w")

        # ── 2. Key Metadata Grid (2x2 Cards) ──
        if not checklist_only:
            meta_grid = ctk.CTkFrame(scroll, fg_color="transparent")
            meta_grid.pack(fill="x", pady=(0, 14))
            meta_grid.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="meta_col")

            meta_items = [
                ("ASSIGNED TO", task.assigned_to or "Unassigned"),
                ("ASSIGNED BY", task.assigned_by or "Manager"),
                ("DATE ASSIGNED", format_date(task.date)),
                ("DEADLINE", format_date(eff_dl) + (" (Ext)" if is_ext else "")),
            ]

            for col_idx, (m_label, m_val) in enumerate(meta_items):
                m_card = ctk.CTkFrame(meta_grid, fg_color="#FFFFFF", corner_radius=10,
                                      border_width=1, border_color=COLORS["border"])
                m_card.grid(row=0, column=col_idx, sticky="ew", padx=4, pady=2)
                ctk.CTkLabel(m_card, text=m_label, font=("Segoe UI", 8, "bold"),
                             text_color=COLORS["text_dim"]).pack(anchor="w", padx=12, pady=(10, 2))
                ctk.CTkLabel(m_card, text=str(m_val), font=("Segoe UI", 12, "bold"),
                             text_color=COLORS["text_main"]).pack(anchor="w", padx=12, pady=(0, 10))

            if is_ext and getattr(task, "reason", None):
                ext_card = ctk.CTkFrame(scroll, fg_color="#FFFBEB", corner_radius=10,
                                        border_width=1, border_color="#FDE68A")
                ext_card.pack(fill="x", pady=(0, 14))
                ctk.CTkLabel(ext_card, text="EXTENSION DETAILS", font=("Segoe UI", 9, "bold"),
                             text_color="#B45309").pack(anchor="w", padx=16, pady=(10, 2))
                ctk.CTkLabel(ext_card, text=str(task.reason), font=("Segoe UI", 11),
                             text_color="#92400E", wraplength=660, justify="left").pack(anchor="w", padx=16, pady=(0, 10))

        # ── 3. Interactive Checklist Section with Visual Progress Bar ──
        has_checklist = bool(getattr(task, 'checklist', None))
        btn_complete = None
        checkbox_vars = []

        if has_checklist:
            chk_section = ctk.CTkFrame(scroll, fg_color="#FFFFFF", corner_radius=12,
                                       border_width=1, border_color=COLORS["border"])
            chk_section.pack(fill="x", pady=(0, 14))

            # Header with Progress Counter
            chk_hdr = ctk.CTkFrame(chk_section, fg_color="transparent")
            chk_hdr.pack(fill="x", padx=18, pady=(16, 8))

            ctk.CTkLabel(chk_hdr, text="Checklist Milestones", font=("Segoe UI", 13, "bold"),
                         text_color=COLORS["text_main"]).pack(side="left")

            lbl_progress = ctk.CTkLabel(chk_hdr, text="", font=("Segoe UI", 10, "bold"),
                                        text_color=COLORS["accent"])
            lbl_progress.pack(side="right")

            if not is_done:
                btn_ai_update = ctk.CTkButton(
                    chk_hdr, text="📝 AI Text Update", width=110, height=26,
                    font=FONTS["small"], corner_radius=6,
                    fg_color="transparent", border_width=1,
                    border_color=COLORS["accent"], text_color=COLORS["accent"],
                    hover_color="#EFF6FF",
                    command=lambda t=task: [dialog.destroy(), self.prompt_task_text_update(t)]
                )
                btn_ai_update.pack(side="right", padx=(0, 10))


            # Progress Bar
            progress_bar = ctk.CTkProgressBar(chk_section, height=6, corner_radius=3,
                                              fg_color="#F1F5F9", progress_color=COLORS["accent"])
            progress_bar.pack(fill="x", padx=18, pady=(0, 14))

            def update_progress_ui():
                total = len(checkbox_vars)
                if total == 0:
                    return
                done = sum(1 for v in checkbox_vars if v.get())
                pct = done / total
                progress_bar.set(pct)
                if done == total:
                    progress_bar.configure(progress_color="#10B981")
                    lbl_progress.configure(text=f"✓ All {total} Milestones Completed (100%)", text_color="#15803D")
                    if btn_complete:
                        btn_complete.configure(state="normal", border_color="#10B981", text_color="#10B981")
                else:
                    progress_bar.configure(progress_color=COLORS["accent"])
                    lbl_progress.configure(text=f"{done} of {total} Completed ({int(pct * 100)}%)", text_color=COLORS["accent"])
                    if btn_complete:
                        btn_complete.configure(state="disabled", border_color=COLORS["border"], text_color=COLORS["text_dim"])

            # Checklist items list
            chk_list_frame = ctk.CTkFrame(chk_section, fg_color="transparent")
            chk_list_frame.pack(fill="x", padx=18, pady=(0, 16))

            for i, item in enumerate(task.checklist):
                is_checked = False
                text = str(item)
                if isinstance(item, dict):
                    is_checked = item.get("completed", False)
                    text = str(item.get("text", "") or item.get("step", "") or item.get("goal", ""))
                elif isinstance(item, str):
                    if item.startswith("[x]"):
                        is_checked = True
                        text = item[3:].strip()
                    elif item.startswith("[ ]"):
                        text = item[3:].strip()

                var = ctk.BooleanVar(value=is_checked)
                checkbox_vars.append(var)

                item_card = ctk.CTkFrame(chk_list_frame, fg_color="#F8FAFC", corner_radius=8,
                                        border_width=1, border_color="#E2E8F0")
                item_card.pack(fill="x", pady=4)
                item_card.grid_columnconfigure(1, weight=1)

                lbl = ctk.CTkLabel(
                    item_card, text=text, font=("Segoe UI", 11),
                    text_color="#94A3B8" if is_checked else COLORS["text_main"],
                    justify="left", wraplength=580, anchor="w"
                )

                def on_toggle(idx=i, v=var, t=task, l=lbl, c_card=item_card):
                    new_state = v.get()
                    l.configure(text_color="#94A3B8" if new_state else COLORS["text_main"])
                    c_card.configure(border_color="#CBD5E1" if new_state else "#E2E8F0")
                    if isinstance(t.checklist[idx], dict):
                        t.checklist[idx]["completed"] = new_state
                    elif isinstance(t.checklist[idx], str):
                        prefix = "[x]" if new_state else "[ ]"
                        base_text = str(t.checklist[idx])
                        if base_text.startswith("[x]") or base_text.startswith("[ ]"):
                            base_text = base_text[3:].strip()
                        t.checklist[idx] = f"{prefix} {base_text}"
                    update_progress_ui()
                    threading.Thread(target=lambda: (self.sheets_client.update_task_checklist(t.task_id, t.checklist), self.after(0, self._full_refresh)), daemon=True).start()

                chk = ctk.CTkCheckBox(item_card, text="", variable=var, command=on_toggle,
                                      width=22, corner_radius=4, border_width=1,
                                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
                chk.grid(row=0, column=0, padx=(12, 8), pady=10, sticky="n")
                lbl.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="w")

        # ── 4. Modern Bottom Actions Bar (Border-only buttons) ──
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 18), padx=22)

        # Complete button (Outline style)
        if not is_done:
            btn_complete = ctk.CTkButton(
                btn_frame, text="✓ Mark as Completed", height=36, corner_radius=8,
                fg_color="transparent", border_width=1.5,
                border_color=COLORS["success"] if not has_checklist else COLORS["border"],
                text_color=COLORS["success"] if not has_checklist else COLORS["text_dim"],
                hover_color="#DCFCE7", font=("Segoe UI", 11, "bold"),
                state="normal" if not has_checklist else "disabled"
            )
            btn_complete.pack(side="left", padx=(0, 10))

            def on_complete_click(t=task, b=btn_complete):
                self.do_inline_update(t, "Completed", b)
                dialog.destroy()

            btn_complete.configure(command=on_complete_click)

        # Delay button (Outline style)
        if not is_done:
            btn_delay = ctk.CTkButton(
                btn_frame, text="⏰ Request Extension", height=36, corner_radius=8,
                fg_color="transparent", border_width=1,
                border_color="#F59E0B", text_color="#D97706",
                hover_color="#FFFBEB", font=FONTS["small"],
                command=lambda t=task: [dialog.destroy(), self.prompt_extension_request(t, None)]
            )
            btn_delay.pack(side="left")

        # Close button (Outline style)
        ctk.CTkButton(
            btn_frame, text="Close", height=36, width=80, corner_radius=8,
            fg_color="transparent", border_width=1,
            border_color=COLORS["border"], text_color=COLORS["text_main"],
            hover_color=COLORS["card_bg"], font=FONTS["small"],
            command=dialog.destroy
        ).pack(side="right")

        if has_checklist:
            update_progress_ui()

    # ── Extension Request Dialog ─────────────────────────────────────────

    def prompt_extension_request(self, task, var=None):
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
            if var:
                var.set(task.status)
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", cancel)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 20))
        ctk.CTkButton(
            btn_frame, text="Submit Request", command=submit,
            fg_color="transparent", border_width=1.5,
            border_color="#F59E0B", text_color="#D97706",
            hover_color="#FFFBEB", font=("Segoe UI", 11, "bold"),
            height=38, width=130, corner_radius=8
        ).pack(side="right", padx=(10, 0))
        ctk.CTkButton(
            btn_frame, text="Cancel", command=cancel,
            fg_color="transparent", border_width=1,
            border_color=COLORS["border"], text_color=COLORS["text_dim"],
            hover_color="#F8FAFC", font=FONTS["small"],
            height=38, width=90, corner_radius=8
        ).pack(side="right")

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
        dialog.geometry("600x620")
        dialog.configure(fg_color="#F8FAFC")
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (600 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (620 // 2)
        dialog.geometry(f"+{max(20, x)}+{max(20, y)}")
        
        fade_in(dialog)

        form = ctk.CTkFrame(dialog, fg_color="#FFFFFF", corner_radius=12,
                            border_width=1, border_color=COLORS["border"])
        form.pack(fill="both", expand=True, padx=22, pady=22)

        # Header with Pill Badge
        hdr_frame = ctk.CTkFrame(form, fg_color="transparent")
        hdr_frame.pack(fill="x", padx=22, pady=(20, 14))

        badge = ctk.CTkLabel(hdr_frame, text="✨ SELF ASSIGN", font=("Segoe UI", 9, "bold"),
                             text_color="#1D4ED8", fg_color="#EFF6FF", corner_radius=4,
                             height=22, width=96)
        badge.pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(hdr_frame, text="Create a Task for Yourself", font=("Segoe UI", 16, "bold"),
                     text_color=COLORS["text_main"]).pack(anchor="w")
        ctk.CTkLabel(hdr_frame, text="Add a new deliverable or goal to your daily focus list",
                     font=FONTS["small"], text_color=COLORS["text_dim"]).pack(anchor="w", pady=(2, 0))

        # Assigned To (read-only — always self)
        row1 = ctk.CTkFrame(form, fg_color="transparent")
        row1.pack(fill="x", padx=22, pady=(0, 12))
        ctk.CTkLabel(row1, text="ASSIGNED TO", font=("Segoe UI", 9, "bold"),
                     text_color=COLORS["text_dim"], width=100, anchor="w").pack(side="left")
        ctk.CTkLabel(row1, text=f"👤 {self.current_user}", font=("Segoe UI", 11, "bold"),
                     text_color="#1D4ED8", fg_color="#EFF6FF", corner_radius=6,
                     height=26, padx=10).pack(side="left")

        # Task Description
        ctk.CTkLabel(form, text="TASK DESCRIPTION", font=("Segoe UI", 9, "bold"),
                     text_color=COLORS["text_dim"]).pack(padx=22, pady=(0, 4), anchor="w")
        task_desc = ctk.CTkTextbox(form, height=95, font=FONTS["body"],
                                   text_color=COLORS["text_main"], fg_color="#F8FAFC",
                                   border_color=COLORS["border"], border_width=1, corner_radius=8)
        task_desc.pack(fill="x", padx=22, pady=(0, 14))

        # Deadline
        row_dl = ctk.CTkFrame(form, fg_color="transparent")
        row_dl.pack(fill="x", padx=22, pady=(0, 14))
        ctk.CTkLabel(row_dl, text="DEADLINE", font=("Segoe UI", 9, "bold"),
                     text_color=COLORS["text_dim"], width=100, anchor="w").pack(side="left")
        dl_entry = DateEntry(row_dl, width=18, date_pattern='dd/mm/yyyy',
                             background=COLORS["sidebar_bg"], foreground='white',
                             borderwidth=2, font=FONTS["body"])
        dl_entry.pack(side="left")

        # Priority Selection with Modern Filter Bar (zero grey box, outline styling)
        row_prio = ctk.CTkFrame(form, fg_color="transparent")
        row_prio.pack(fill="x", padx=22, pady=(0, 16))
        ctk.CTkLabel(row_prio, text="PRIORITY", font=("Segoe UI", 9, "bold"),
                     text_color=COLORS["text_dim"], width=100, anchor="w").pack(side="left")

        prio_color_map = {
            "Low": "#64748B",
            "Normal": "#2563EB",
            "High": "#D97706",
            "Urgent": "#DC2626"
        }
        prio_combo = ModernFilterBar(
            row_prio, values=["Low", "Normal", "High", "Urgent"],
            default_val="Normal", color_map=prio_color_map
        )
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

        # Action Buttons (Outline Border-only style)
        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", padx=22, pady=(10, 20))

        ctk.CTkButton(
            btn_row, text="Create Task", command=submit_task,
            fg_color="transparent", border_width=1.5,
            border_color=COLORS["accent"], text_color=COLORS["accent"],
            hover_color="#EFF6FF", font=("Segoe UI", 11, "bold"),
            height=38, width=130, corner_radius=8
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_row, text="Cancel", command=dialog.destroy,
            fg_color="transparent", border_width=1,
            border_color=COLORS["border"], text_color=COLORS["text_dim"],
            hover_color="#F8FAFC", font=FONTS["small"],
            height=38, width=90, corner_radius=8
        ).pack(side="right")

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

    def do_inline_update(self, task, new_status, btn_widget, skip_modal=False):
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
                    if not skip_modal:
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
                    if task.task_id in self._task_rows and "status_var" in self._task_rows[task.task_id]:
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
