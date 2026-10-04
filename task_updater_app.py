import customtkinter as ctk
import tkinter as tk
import json
import time
import os
import sys
import threading
from tkinter import messagebox
from config import COLORS, FONTS, DEPARTMENTS

# Double all font sizes for task_updater_app
FONTS = {
    key: (val[0], val[1] * 2, *val[2:]) if isinstance(val, (tuple, list)) else val
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
from services.sheets_client import SheetsClient
from services.extension_store import (
    submit_extension_request,
    get_requests_for_employee,
)
from tkcalendar import DateEntry
from datetime import datetime

# Resolve paths relative to exe directory when frozen
if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

CACHE_FILE = os.path.join(_APP_DIR, "recent_task_updates.json")

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

class TaskUpdaterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Light")
        self.title("Stauff - Update Task Status")
        self.geometry("1050x900")
        self.configure(fg_color=COLORS["bg"])

        try:
            self.iconbitmap(os.path.join(_APP_DIR, "user.ico"))
        except Exception:
            pass

        self.n8n_client = N8nClient()
        self.sheets_client = SheetsClient()

        self.departments = DEPARTMENTS
        self.current_tasks = []       # all tasks fetched for the employee
        self.status_vars = {}         # maps task_id → tk.StringVar
        self.modified_task_info = {}  # maps task_id → dict of modifications

        self.current_dept = None
        self.current_user = None

        # Sorting / filtering state
        self._sort_key = "deadline_asc"   # default sort
        self._filter_status = "Active"    # Active | All | Completed

        self.setup_login_ui()

    # ═════════════════════════════════════════════════════════════════════
    # Login Screen
    # ═════════════════════════════════════════════════════════════════════

    def setup_login_ui(self):
        self.login_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.login_frame.pack(fill="both", expand=True, padx=20, pady=20)

        card = ctk.CTkFrame(self.login_frame, fg_color=COLORS["card_bg"], corner_radius=8)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text="Welcome", font=FONTS["header"],
                     text_color=COLORS["text_main"]).pack(pady=(30, 10), padx=50)
        ctk.CTkLabel(card, text="Please select your department and name",
                     font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=(0, 20), padx=50)

        self.login_combo_dept = ModernComboBox(
            card, values=list(self.departments.keys()),
            command=self.on_login_dept_select, width=400, height=48,
            font=FONTS["body"], dropdown_font=FONTS["body"], corner_radius=8)
        self.login_combo_dept.pack(pady=(0, 15), padx=50)

        self.login_combo_person = ModernComboBox(
            card, values=[], width=400, height=48,
            font=FONTS["body"], dropdown_font=FONTS["body"], corner_radius=8)
        self.login_combo_person.pack(pady=(0, 25), padx=50)

        ctk.CTkButton(card, text="Continue", font=FONTS["body_bold"],
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
        
        avatar_lbl = ctk.CTkLabel(left_header, text="👤", font=("Segoe UI", 28))
        avatar_lbl.pack(side="left", padx=(0, 12))
        
        user_info = ctk.CTkFrame(left_header, fg_color="transparent")
        user_info.pack(side="left")
        ctk.CTkLabel(user_info, text=self.current_user, font=FONTS["body_bold"], text_color=COLORS["text_main"]).pack(anchor="w")
        ctk.CTkLabel(user_info, text=self.current_dept, font=FONTS["small"], text_color=COLORS["text_dim"]).pack(anchor="w")

        btn_frame = ctk.CTkFrame(header_bar, fg_color="transparent")
        btn_frame.pack(side="right", padx=24, pady=8)

        ctk.CTkButton(btn_frame, text="＋ Add Task", width=110, height=36,
                      font=FONTS["body_bold"], fg_color=COLORS["accent"], text_color="#FFFFFF", corner_radius=6,
                      hover_color=COLORS["accent_hover"],
                      command=self._show_add_task_dialog).pack(side="left", padx=(0, 12))

        ctk.CTkButton(btn_frame, text="↻ Refresh", width=90, height=36,
                      font=FONTS["body_bold"], fg_color="#FFFFFF", text_color=COLORS["primary_navy"], corner_radius=6,
                      border_width=1, border_color=COLORS["border"], hover_color=COLORS["bg"],
                      command=self._full_refresh).pack(side="left")

        # ── Scrollable body ──
        self.body_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body_scroll.pack(fill="both", expand=True, padx=24, pady=16)
        self.body_scroll.grid_columnconfigure(0, weight=1)

        self._build_dashboard_content()

    def _build_dashboard_content(self):
        for w in self.body_scroll.winfo_children():
            w.destroy()

        loading_lbl = ctk.CTkLabel(self.body_scroll, text="Loading data, please wait...", font=FONTS["body"], text_color=COLORS["text_dim"])
        loading_lbl.pack(pady=40)
        
        def fetch_data_thread():
            try:
                self._fetch_tasks_data()
                ext_requests = get_requests_for_employee(self.current_user or "")
            except Exception as e:
                print(f"Error fetching data: {e}")
                ext_requests = []
            self.after(0, lambda: self._render_dashboard_content(loading_lbl, ext_requests))
            
        threading.Thread(target=fetch_data_thread, daemon=True).start()

    def _render_dashboard_content(self, loading_lbl, ext_requests):
        if loading_lbl.winfo_exists():
            loading_lbl.destroy()
            
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

        self._build_kpi_section(
            self.body_scroll,
            total=len(all_tasks),
            active=len(active_tasks),
            completed=len(completed_tasks),
            overdue=len(overdue_tasks),
            due_today=len(due_today_tasks),
            due_this_week=len(due_this_week),
            high_priority=len(high_priority),
            pending_extensions=len(pending_ext),
        )

        columns_frame = ctk.CTkFrame(self.body_scroll, fg_color="transparent")
        columns_frame.pack(fill="both", expand=True)
        columns_frame.grid_columnconfigure(0, weight=7)
        columns_frame.grid_columnconfigure(1, weight=3)

        left_col = ctk.CTkFrame(columns_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right_col = ctk.CTkFrame(columns_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_task_list_section(left_col, all_tasks, today)
        self._build_extension_section(right_col, ext_requests)

    def _build_kpi_section(self, parent, **kpis):
        kpi_outer = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_outer.pack(fill="x", pady=(0, 20))

        cards_data = [
            ("Total Tasks",      str(kpis["total"]),             "#F1F5F9", "#0F172A"),
            ("Active",           str(kpis["active"]),             "#EFF6FF", "#1E3A8A"),
            ("Completed",        str(kpis["completed"]),          "#ECFDF5", "#065F46"),
            ("Overdue",          str(kpis["overdue"]),            "#FEF2F2", "#991B1B"),
            ("Due Today",        str(kpis["due_today"]),          "#FFFBEB", "#92400E"),
            ("Due This Week",    str(kpis["due_this_week"]),      "#F8FAFC", "#334155"),
            ("High / Urgent",    str(kpis["high_priority"]),      "#FEF2F2", "#991B1B"),
            ("Pending Ext.",     str(kpis["pending_extensions"]), "#F5F3FF", "#4C1D95"),
        ]

        for row_idx in range(2):
            row_frame = ctk.CTkFrame(kpi_outer, fg_color="transparent")
            row_frame.pack(fill="x", pady=6)
            for col_idx in range(4):
                row_frame.grid_columnconfigure(col_idx, weight=1, uniform="kpi_col")
                
            for col_idx in range(4):
                i = row_idx * 4 + col_idx
                if i >= len(cards_data):
                    break
                label, value, bg_color, txt_color = cards_data[i]
                
                card = ctk.CTkFrame(row_frame, fg_color=bg_color,
                                    corner_radius=12, border_width=1, border_color=COLORS["border"])
                card.grid(row=0, column=col_idx, sticky="nsew", padx=8, pady=2)

                ctk.CTkLabel(card, text=value, font=(FONTS["header"][0], 32, "bold"),
                             text_color=txt_color, fg_color="transparent").pack(anchor="w", padx=20, pady=(20, 0))
                ctk.CTkLabel(card, text=label, font=FONTS["body_bold"],
                             text_color=txt_color, fg_color="transparent").pack(anchor="w", padx=20, pady=(4, 20))

    def _build_task_list_section(self, parent, all_tasks, today):
        section = ctk.CTkFrame(parent, fg_color=COLORS["card_bg"],
                               corner_radius=12, border_width=1, border_color=COLORS["border"])
        section.pack(fill="both", expand=True)

        hdr = ctk.CTkFrame(section, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(24, 16))
        
        title_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        title_frame.pack(side="left")
        ctk.CTkLabel(title_frame, text="My Tasks", font=("Segoe UI", 24, "bold"), text_color=COLORS["text_main"]).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Tasks assigned to you and their current status", 
                     font=FONTS["body"], text_color=COLORS["text_dim"]).pack(anchor="w", pady=(2, 0))

        toolbar = ctk.CTkFrame(hdr, fg_color="transparent")
        toolbar.pack(side="right", pady=4)
        
        self.filter_combo = ModernComboBox(
            toolbar, values=["Active", "All", "Completed", "Overdue", "Delayed", "High Priority"],
            width=170, height=36, font=FONTS["body"], dropdown_font=FONTS["body"], corner_radius=6,
            command=lambda _: self._on_sort_filter_change())
        self.filter_combo.set(self._filter_status)
        self.filter_combo.pack(side="right", padx=(8, 0))

        self.sort_combo = ModernComboBox(
            toolbar, values=["Deadline ↑", "Deadline ↓", "Priority ↓", "Assigned ↑"],
            width=170, height=36, font=FONTS["body"], dropdown_font=FONTS["body"], corner_radius=6,
            command=lambda _: self._on_sort_filter_change())
        self.sort_combo.set("Deadline ↑")
        self.sort_combo.pack(side="right", padx=(8, 0))
        
        self.tasks_container = ctk.CTkFrame(section, fg_color="transparent")
        self.tasks_container.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        self.tasks_container.grid_columnconfigure(0, weight=1)

        self._render_sorted_filtered_tasks(all_tasks, today)
    def _on_sort_filter_change(self):
        self._filter_status = self.filter_combo.get()
        today = datetime.now().date()
        self._render_sorted_filtered_tasks(self.current_tasks, today)

    def _render_sorted_filtered_tasks(self, all_tasks, today):
        for w in self.tasks_container.winfo_children():
            w.destroy()
        self.status_vars.clear()
        self.modified_task_info.clear()

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

        sort_val = self.sort_combo.get() if hasattr(self, "sort_combo") else "Deadline ↑"
        far_future = datetime(2099, 12, 31).date()
        far_past = datetime(2000, 1, 1).date()

        if "Deadline ↑" in sort_val:
            tasks.sort(key=lambda t: t._effective_deadline_date or far_future)
        elif "Deadline ↓" in sort_val:
            tasks.sort(key=lambda t: t._effective_deadline_date or far_past, reverse=True)
        elif "Priority" in sort_val:
            prio_order = {"urgent": 0, "high": 1, "medium": 2, "normal": 2, "low": 3}
            tasks.sort(key=lambda t: prio_order.get(t.priority.lower(), 9))
        elif "Assigned" in sort_val:
            tasks.sort(key=lambda t: _parse_deadline(t.date) or far_past)

        if not tasks:
            empty_frame = ctk.CTkFrame(self.tasks_container, fg_color="transparent")
            empty_frame.pack(pady=40)
            ctk.CTkLabel(empty_frame, text="No active tasks", font=FONTS["subheader"], text_color=COLORS["text_main"]).pack()
            ctk.CTkLabel(empty_frame, text="You currently have no tasks matching this filter.", font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=(5, 15))
            ctk.CTkButton(empty_frame, text="View All Tasks", font=FONTS["body_bold"], fg_color="transparent",
                          border_width=1, border_color=COLORS["border"], text_color=COLORS["text_main"], hover_color=COLORS["bg"],
                          command=lambda: [self.filter_combo.set("All"), self._on_sort_filter_change()]).pack()
            return

        for idx, task in enumerate(tasks):
            self._build_task_row(idx, task, today)

    def _build_task_row(self, idx, task, today):
        row = ctk.CTkFrame(self.tasks_container, fg_color="transparent", border_width=0)
        row.grid(row=idx, column=0, sticky="ew", pady=4)
        row.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(row, fg_color=COLORS["card_bg"], border_width=1, border_color=COLORS["border"], corner_radius=8)
        inner.grid(row=0, column=0, sticky="ew", pady=2)
        inner.grid_columnconfigure(1, weight=1)

        def bind_double_click(widget, t=task):
            widget.bind("<Double-1>", lambda event, tk=t: self.show_task_details_dialog(tk))
        bind_double_click(inner)

        left_info = ctk.CTkFrame(inner, fg_color="transparent")
        left_info.grid(row=0, column=0, padx=20, pady=16, sticky="w")
        
        ctk.CTkLabel(left_info, text=task.task_id, font=FONTS["small"], text_color=COLORS["text_dim"]).pack(anchor="w")
        
        prio_color = COLORS["error"] if task.priority.lower() in ("high", "urgent") else (COLORS["warning"] if task.priority.lower() in ("medium", "normal") else COLORS["text_dim"])
        ctk.CTkLabel(left_info, text=task.priority.upper(), font=("Segoe UI", 9, "bold"), text_color=prio_color).pack(anchor="w", pady=(2, 0))

        mid_info = ctk.CTkFrame(inner, fg_color="transparent")
        mid_info.grid(row=0, column=1, padx=16, pady=16, sticky="w")
        desc = task.description
        if len(desc) > 80: desc = desc[:80] + "..."
        lbl_desc = ctk.CTkLabel(mid_info, text=desc, font=("Segoe UI", 18, "bold"), text_color=COLORS["text_main"], justify="left")
        lbl_desc.pack(anchor="w")
        bind_double_click(lbl_desc)

        right_info = ctk.CTkFrame(inner, fg_color="transparent")
        right_info.grid(row=0, column=2, padx=20, pady=16, sticky="e")
        
        eff_dl = task._effective_deadline
        dl_str = format_date(eff_dl)
        dl_color = COLORS["text_dim"]
        if task._effective_deadline_date and task._effective_deadline_date < today and task.status.lower() not in ("completed", "done"):
            dl_color = COLORS["error"]
        
        ctk.CTkLabel(right_info, text=f"Due: {dl_str}", font=FONTS["small"], text_color=dl_color).pack(anchor="e", pady=(0, 4))

        status_color = COLORS["success"] if task.status.lower() in ("completed", "done") else (COLORS["info"] if task.status.lower() == "active" else COLORS["warning"])
        ctk.CTkLabel(right_info, text=task.status.upper(), font=("Segoe UI", 10, "bold"), text_color=status_color).pack(anchor="e")
        
        actions_frame = ctk.CTkFrame(inner, fg_color="transparent")
        actions_frame.grid(row=0, column=3, padx=20, pady=16, sticky="e")

        status_var = ctk.StringVar(value="Status...")
        status_combo = ModernComboBox(actions_frame, values=["Pending", "Delayed", "Completed"], 
                                      variable=status_var, width=140, height=32, font=FONTS["small"], dropdown_font=FONTS["small"],
                                      corner_radius=6)
        status_combo.pack(side="left", padx=(0, 8))
        
        btn_update = ctk.CTkButton(actions_frame, text="Update", width=60, height=32, font=FONTS["small"], corner_radius=6,
                                   fg_color=COLORS["accent"], text_color="#FFFFFF", hover_color=COLORS["accent_hover"])
        btn_update.configure(command=lambda t=task, c=status_combo, b=btn_update: self.do_inline_update(t, c.get(), b))
        btn_update.pack(side="left", padx=(0, 8))

        btn_view = ctk.CTkButton(actions_frame, text="View", width=60, height=32, font=FONTS["small"], corner_radius=6,
                                 fg_color="transparent", border_width=1, border_color=COLORS["border"],
                                 text_color=COLORS["text_main"], hover_color=COLORS["bg"],
                                 command=lambda t=task: self.show_task_details_dialog(t))
        btn_view.pack(side="left")


    # ── Task Detail Dialog ───────────────────────────────────────────────

    def show_task_details_dialog(self, task):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Task Details: {task.task_id}")
        dialog.geometry("500x600")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (500 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (600 // 2)
        dialog.geometry(f"+{x}+{y}")

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        eff_dl = getattr(task, "_effective_deadline", task.deadline)
        is_ext = getattr(task, "_is_extended", False)

        details = [
            ("Task ID", task.task_id),
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
            ctk.CTkLabel(scroll, text=f"{label}:", font=FONTS["body_bold"],
                         text_color=COLORS["text_main"]).pack(anchor="w", pady=(10, 0))
            ctk.CTkLabel(scroll, text=str(value) if value else "N/A", font=FONTS["body"],
                         text_color=COLORS["text_dim"], wraplength=450,
                         justify="left").pack(anchor="w")

        ctk.CTkLabel(scroll, text="Description:", font=FONTS["body_bold"],
                     text_color=COLORS["text_main"]).pack(anchor="w", pady=(10, 0))
        desc_box = ctk.CTkTextbox(scroll, height=120, font=FONTS["body"],
                                  text_color=COLORS["text_dim"], fg_color=COLORS["input_bg"])
        desc_box.insert("1.0", str(task.description))
        desc_box.configure(state="disabled")
        desc_box.pack(fill="x", pady=(5, 10))

        ctk.CTkButton(dialog, text="Close", command=dialog.destroy,
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"]).pack(pady=20)

    # ── Extension Request Dialog ─────────────────────────────────────────

    def prompt_extension_request(self, task, var):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Request Deadline Extension")
        dialog.geometry("540x580")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (540 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (580 // 2)
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text=f"Task: [{task.task_id}]", font=FONTS["body_bold"],
                     text_color=COLORS["text_main"]).pack(pady=(20, 2), padx=20, anchor="w")
        ctk.CTkLabel(dialog, text=f"Current Deadline: {format_date(task.deadline)}",
                     font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=(0, 10), padx=20, anchor="w")

        ctk.CTkLabel(dialog, text="Reason for Extension:", font=FONTS["body_bold"],
                     text_color=COLORS["text_main"]).pack(pady=(5, 3), padx=20, anchor="w")
        reason_text = ctk.CTkTextbox(dialog, height=90, font=FONTS["body"],
                                     text_color=COLORS["text_main"], fg_color=COLORS["input_bg"],
                                     border_color=COLORS["border"], border_width=1)
        reason_text.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(dialog, text="Requested New Deadline:", font=FONTS["body_bold"],
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
                      font=FONTS["body_bold"], height=40, width=140).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_frame, text="Cancel", command=cancel,
                      fg_color="transparent", border_width=1, border_color=COLORS["border"],
                      text_color=COLORS["text_main"], hover_color=COLORS["card_bg"],
                      font=FONTS["body"], height=40, width=100).pack(side="right")

    # ── Extension Requests Display ───────────────────────────────────────

    def _build_extension_section(self, parent, ext_requests):
        section = ctk.CTkFrame(parent, fg_color=COLORS["card_bg"],
                               corner_radius=12, border_width=1, border_color=COLORS["border"])
        section.pack(fill="both", expand=True)

        hdr = ctk.CTkFrame(section, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(24, 16))
        
        title_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        title_frame.pack(side="left")
        ctk.CTkLabel(title_frame, text="My Extension Requests", font=("Segoe UI", 24, "bold"), text_color=COLORS["text_main"]).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Track your deadline change requests", 
                     font=FONTS["body"], text_color=COLORS["text_dim"]).pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(hdr, text="↻", width=36, font=FONTS["body_bold"], corner_radius=6,
                      fg_color="transparent", border_width=1, border_color=COLORS["border"], text_color=COLORS["text_main"], hover_color=COLORS["bg"],
                      height=36, command=self._full_refresh).pack(side="right")

        container = ctk.CTkFrame(section, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        if not ext_requests:
            ctk.CTkLabel(container, text="No extension requests yet.", font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=40)
            return

        for idx, req in enumerate(reversed(ext_requests)):
            status = req["status"]
            if status == "Pending":
                badge_color, badge_text = COLORS["warning"], "PENDING"
            elif status == "Approved":
                badge_color, badge_text = COLORS["success"], "APPROVED"
            else:
                badge_color, badge_text = COLORS["error"], "REJECTED"

            card = ctk.CTkFrame(container, fg_color="transparent", border_width=1, border_color=COLORS["border"], corner_radius=8)
            card.pack(fill="x", pady=6)
            
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=16, pady=(16, 8))
            
            ctk.CTkLabel(top_row, text=badge_text, font=("Segoe UI", 9, "bold"), 
                         text_color="#FFFFFF", fg_color=badge_color, corner_radius=4, 
                         width=70, height=22).pack(side="left")
            
            ctk.CTkLabel(card, text=req["task_id"], font=FONTS["body_bold"], text_color=COLORS["text_main"]).pack(anchor="w", padx=16)
            
            desc = req["task_description"]
            if len(desc) > 40: desc = desc[:40] + "..."
            ctk.CTkLabel(card, text=desc, font=FONTS["body"], text_color=COLORS["text_dim"]).pack(anchor="w", padx=16, pady=(4, 12))
            
            bot_row = ctk.CTkFrame(card, fg_color=COLORS["bg"], corner_radius=0)
            bot_row.pack(fill="x", padx=1, pady=(0, 1))
            
            if status == "Approved":
                final_deadline = format_date(req.get("manager_deadline") or req["requested_deadline"])
                dl_lbl = f"New Deadline: {final_deadline}"
            elif status == "Rejected":
                dl_lbl = f"Unchanged: {format_date(req['current_deadline'])}"
            else:
                dl_lbl = f"Requested: {format_date(req['requested_deadline'])}"
                
            ctk.CTkLabel(bot_row, text=dl_lbl, font=FONTS["body"], text_color=COLORS["text_main"]).pack(anchor="w", padx=16, pady=10)
            
            if status != "Pending" and req.get("manager_note"):
                ctk.CTkLabel(card, text=f"Note: {req['manager_note']}", font=FONTS["small"], text_color=COLORS["text_dim"], wraplength=220).pack(anchor="w", padx=16, pady=(0, 12))


    # ── Add Task Dialog (self-assign only) ───────────────────────────────

    def _show_add_task_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Task")
        dialog.geometry("520x560")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (520 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (560 // 2)
        dialog.geometry(f"+{x}+{y}")

        form = ctk.CTkFrame(dialog, fg_color=COLORS["card_bg"], corner_radius=8)
        form.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(form, text="Create a Task for Yourself", font=FONTS["subheader"],
                     text_color=COLORS["text_main"]).pack(pady=(20, 15), padx=20, anchor="w")

        # Assigned To (read-only — always self)
        row1 = ctk.CTkFrame(form, fg_color="transparent")
        row1.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(row1, text="Assigned To:", font=FONTS["body_bold"],
                     text_color=COLORS["text_main"], width=140, anchor="w").pack(side="left")
        ctk.CTkLabel(row1, text=self.current_user, font=FONTS["body"],
                     text_color=COLORS["accent"]).pack(side="left", padx=5)

        # Task Description
        ctk.CTkLabel(form, text="Task Description:", font=FONTS["body_bold"],
                     text_color=COLORS["text_main"]).pack(padx=20, pady=(10, 3), anchor="w")
        task_desc = ctk.CTkTextbox(form, height=100, font=FONTS["body"],
                                   text_color=COLORS["text_main"], fg_color=COLORS["input_bg"],
                                   border_color=COLORS["border"], border_width=1)
        task_desc.pack(fill="x", padx=20, pady=(0, 10))

        # Deadline
        row_dl = ctk.CTkFrame(form, fg_color="transparent")
        row_dl.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(row_dl, text="Deadline:", font=FONTS["body_bold"],
                     text_color=COLORS["text_main"], width=140, anchor="w").pack(side="left")
        dl_entry = DateEntry(row_dl, width=20, date_pattern='dd/mm/yyyy',
                             background=COLORS["sidebar_bg"], foreground='white',
                             borderwidth=2, font=FONTS["body"])
        dl_entry.pack(side="left")

        # Priority
        row_prio = ctk.CTkFrame(form, fg_color="transparent")
        row_prio.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(row_prio, text="Priority:", font=FONTS["body_bold"],
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
                      font=FONTS["body_bold"], height=42, width=160).pack(side="right", padx=(10, 0))
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
            self.current_tasks = []
            print(f"Failed to fetch tasks: {e}")

    def _full_refresh(self):
        """Re-fetch data and rebuild the entire dashboard."""
        self._build_dashboard_content()

    # ── Submit Updates ───────────────────────────────────────────────────

    def do_inline_update(self, task, new_status, btn_widget):
        if not new_status or new_status == "Status...":
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
