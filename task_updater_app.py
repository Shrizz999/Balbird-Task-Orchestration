import customtkinter as ctk
import tkinter as tk
import json
import time
import os
import sys
from tkinter import messagebox
from config import COLORS, FONTS, DEPARTMENTS

# Double all font sizes for task_updater_app
FONTS = {
    key: (val[0], val[1] * 2, *val[2:]) if isinstance(val, (tuple, list)) else val
    for key, val in FONTS.items()
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

        self.login_combo_dept = ctk.CTkComboBox(
            card, values=list(self.departments.keys()),
            command=self.on_login_dept_select, width=400, height=48,
            font=FONTS["body"], dropdown_font=FONTS["body"], corner_radius=8,
            fg_color="#ffffff", border_color="#cbd5e1", border_width=1,
            button_color="#64748b", button_hover_color="#475569",
            dropdown_hover_color="#f1f5f9", dropdown_fg_color="#ffffff",
            dropdown_text_color=COLORS["text_main"], text_color=COLORS["text_main"])
        self.login_combo_dept.pack(pady=(0, 15), padx=50)

        self.login_combo_person = ctk.CTkComboBox(
            card, values=[], width=400, height=48,
            font=FONTS["body"], dropdown_font=FONTS["body"], corner_radius=8,
            fg_color="#ffffff", border_color="#cbd5e1", border_width=1,
            button_color="#64748b", button_hover_color="#475569",
            dropdown_hover_color="#f1f5f9", dropdown_fg_color="#ffffff",
            dropdown_text_color=COLORS["text_main"], text_color=COLORS["text_main"])
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
        header_bar = ctk.CTkFrame(self, fg_color=COLORS["card_bg"], corner_radius=0, height=56)
        header_bar.pack(fill="x")
        header_bar.pack_propagate(False)

        ctk.CTkLabel(header_bar, text=f"👤  {self.current_user}",
                     font=FONTS["subheader"], text_color=COLORS["text_main"]).pack(side="left", padx=20)
        ctk.CTkLabel(header_bar, text=f"Department: {self.current_dept}",
                     font=FONTS["body"], text_color=COLORS["text_dim"]).pack(side="left", padx=(0, 20))

        btn_frame = ctk.CTkFrame(header_bar, fg_color="transparent")
        btn_frame.pack(side="right", padx=15)

        ctk.CTkButton(btn_frame, text="＋ Add Task", width=120, height=36,
                      font=FONTS["body_bold"], fg_color=COLORS["accent"],
                      hover_color=COLORS["accent_hover"],
                      command=self._show_add_task_dialog).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_frame, text="↻ Refresh", width=100, height=36,
                      font=FONTS["body_bold"], fg_color="#475569",
                      hover_color="#334155",
                      command=self._full_refresh).pack(side="left")

        # ── Scrollable body ──
        self.body_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body_scroll.pack(fill="both", expand=True, padx=15, pady=10)
        self.body_scroll.grid_columnconfigure(0, weight=1)

        # All sub-sections are built inside the scroll
        self._build_dashboard_content()

    # ── Build / rebuild everything inside the scroll ─────────────────────

    def _build_dashboard_content(self):
        for w in self.body_scroll.winfo_children():
            w.destroy()

        # Fetch data
        self._fetch_tasks_data()

        today = datetime.now().date()
        all_tasks = self.current_tasks
        ext_requests = get_requests_for_employee(self.current_user or "")

        # Build approved extensions map for deadline overrides
        self._approved_ext = {}
        for req in ext_requests:
            if req.get("status") == "Approved":
                self._approved_ext[req["task_id"]] = req.get("manager_deadline") or req.get("requested_deadline")

        # Compute effective deadlines for each task
        for t in all_tasks:
            eff_dl = self._approved_ext.get(t.task_id, t.deadline)
            t._effective_deadline = eff_dl
            t._effective_deadline_date = _parse_deadline(eff_dl)
            t._is_extended = t.task_id in self._approved_ext

        # ── KPI computation ──
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

        # ── 1. KPI Cards ──
        self._build_kpi_section(
            total=len(all_tasks),
            active=len(active_tasks),
            completed=len(completed_tasks),
            overdue=len(overdue_tasks),
            due_today=len(due_today_tasks),
            due_this_week=len(due_this_week),
            high_priority=len(high_priority),
            pending_extensions=len(pending_ext),
        )

        # ── 2. Attention Required ──
        attention_tasks = []
        for t in active_tasks:
            reasons = []
            if t._effective_deadline_date:
                days_left = (t._effective_deadline_date - today).days
                if days_left < 0:
                    reasons.append(f"🔴 {abs(days_left)} day(s) overdue")
                elif days_left == 0:
                    reasons.append("🟠 Due today")
                elif days_left <= 2:
                    reasons.append(f"🟡 Due in {days_left} day(s)")
            if t.priority.lower() in ("high", "urgent"):
                reasons.append(f"⚡ {t.priority} priority")
            if reasons:
                attention_tasks.append((t, reasons))

        if attention_tasks:
            self._build_attention_section(attention_tasks)

        # ── 3. Task List with sort / filter bar ──
        self._build_task_list_section(all_tasks, today)

        # ── 4. Submit button ──
        self.btn_submit_updates = ctk.CTkButton(
            self.body_scroll, text="Update Statuses Directly",
            font=FONTS["body_bold"], fg_color="#1e293b",
            hover_color="#334155", height=44,
            command=self.submit_updates_only)
        self.btn_submit_updates.pack(fill="x", padx=5, pady=(10, 5))

        # ── 5. Extension Requests ──
        self._build_extension_section(ext_requests)

    # ── KPI Section ──────────────────────────────────────────────────────

    def _build_kpi_section(self, **kpis):
        kpi_outer = ctk.CTkFrame(self.body_scroll, fg_color="transparent")
        kpi_outer.pack(fill="x", pady=(0, 10))

        # Using a sleek, muted gray/slate palette instead of bright rainbow colors
        cards_data = [
            ("Total Tasks",      str(kpis["total"]),             COLORS["text_main"]),
            ("Active",           str(kpis["active"]),             "#475569"),
            ("Completed",        str(kpis["completed"]),          "#059669"),
            ("Overdue",          str(kpis["overdue"]),            "#dc2626"),
            ("Due Today",        str(kpis["due_today"]),          "#d97706"),
            ("Due This Week",    str(kpis["due_this_week"]),      "#64748b"),
            ("High / Urgent",    str(kpis["high_priority"]),      "#991b1b"),
            ("Pending Ext.",     str(kpis["pending_extensions"]), "#0d9488"),
        ]

        # Two rows of four
        for row_idx in range(2):
            row_frame = ctk.CTkFrame(kpi_outer, fg_color="transparent")
            row_frame.pack(fill="x", pady=3)
            for col_idx in range(4):
                i = row_idx * 4 + col_idx
                if i >= len(cards_data):
                    break
                label, value, color = cards_data[i]
                row_frame.grid_columnconfigure(col_idx, weight=1)
                card = ctk.CTkFrame(row_frame, fg_color=COLORS["card_bg"],
                                    corner_radius=8, border_width=1, border_color=COLORS["border"])
                card.grid(row=0, column=col_idx, sticky="ew", padx=4, pady=2)

                # Colored top strip
                strip = ctk.CTkFrame(card, fg_color=color, height=3, corner_radius=0)
                strip.pack(fill="x")

                ctk.CTkLabel(card, text=value, font=(FONTS["header"][0], FONTS["header"][1], "bold"),
                             text_color=COLORS["text_main"]).pack(pady=(8, 0))
                ctk.CTkLabel(card, text=label, font=FONTS["small"],
                             text_color=COLORS["text_dim"]).pack(pady=(0, 8))

    # ── Attention Required Section ───────────────────────────────────────

    def _build_attention_section(self, attention_tasks):
        section = ctk.CTkFrame(self.body_scroll, fg_color=COLORS["card_bg"],
                               corner_radius=8, border_width=1, border_color="#fee2e2")
        section.pack(fill="x", pady=(0, 10), padx=2)

        header = ctk.CTkFrame(section, fg_color="#fef2f2", corner_radius=8)
        header.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(header, text="⚠  Attention Required", font=FONTS["subheader"],
                     text_color="#991b1b").pack(anchor="w", padx=15, pady=8)

        for task, reasons in attention_tasks[:8]:  # cap at 8 to avoid clutter
            row = ctk.CTkFrame(section, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            row.grid_columnconfigure(1, weight=1)

            # Priority badge
            if task.priority.lower() == "urgent":
                badge_color = "#dc2626"
            elif task.priority.lower() == "high":
                badge_color = "#475569"
            else:
                badge_color = COLORS["text_dim"]

            ctk.CTkLabel(row, text=task.priority, font=(FONTS["small"][0], FONTS["small"][1], "bold"),
                         text_color="white", fg_color=badge_color,
                         corner_radius=4, width=70, height=22).grid(row=0, column=0, padx=(0, 8))

            # Task description (truncated)
            desc = task.description
            if len(desc) > 70:
                desc = desc[:70] + "…"
            ctk.CTkLabel(row, text=f"[{task.task_id}] {desc}",
                         font=FONTS["body"], text_color=COLORS["text_main"],
                         anchor="w").grid(row=0, column=1, sticky="w")

            # Reason tags
            reasons_str = "  ·  ".join(reasons)
            ctk.CTkLabel(row, text=reasons_str, font=FONTS["small"],
                         text_color=COLORS["error"]).grid(row=0, column=2, padx=(10, 5))

        # Bottom padding
        ctk.CTkFrame(section, fg_color="transparent", height=6).pack()

    # ── Task List Section (Sort + Filter + Cards) ────────────────────────

    def _build_task_list_section(self, all_tasks, today):
        section = ctk.CTkFrame(self.body_scroll, fg_color=COLORS["card_bg"],
                               corner_radius=8, border_width=1, border_color=COLORS["border"])
        section.pack(fill="x", pady=(0, 5), padx=2)

        # ── Toolbar: Filter + Sort ──
        toolbar = ctk.CTkFrame(section, fg_color="transparent")
        toolbar.pack(fill="x", padx=15, pady=(12, 8))

        ctk.CTkLabel(toolbar, text="Tasks", font=FONTS["subheader"],
                     text_color=COLORS["text_main"]).pack(side="left")

        # Sort dropdown
        self.sort_combo = ctk.CTkComboBox(
            toolbar,
            values=["Deadline ↑ (soonest)", "Deadline ↓ (farthest)",
                    "Priority ↓ (urgent first)", "Assigned Date ↑"],
            width=230, height=36, font=FONTS["small"],
            dropdown_font=FONTS["small"], corner_radius=6,
            fg_color="#f8fafc", border_color="#cbd5e1", border_width=1,
            button_color="#1e293b", button_hover_color="#334155",
            dropdown_hover_color="#e2e8f0", dropdown_fg_color="#ffffff",
            dropdown_text_color=COLORS["text_main"], text_color=COLORS["text_main"],
            command=lambda _: self._on_sort_filter_change())
        self.sort_combo.set("Deadline ↑ (soonest)")
        self.sort_combo.pack(side="right", padx=(4, 0))

        ctk.CTkLabel(toolbar, text="Sort:", font=FONTS["small"],
                     text_color=COLORS["text_dim"]).pack(side="right", padx=(12, 4))

        # Filter dropdown
        self.filter_combo = ctk.CTkComboBox(
            toolbar,
            values=["Active", "All", "Completed", "Overdue", "Delayed", "High Priority"],
            width=160, height=36, font=FONTS["small"],
            dropdown_font=FONTS["small"], corner_radius=6,
            fg_color="#f8fafc", border_color="#cbd5e1", border_width=1,
            button_color="#1e293b", button_hover_color="#334155",
            dropdown_hover_color="#e2e8f0", dropdown_fg_color="#ffffff",
            dropdown_text_color=COLORS["text_main"], text_color=COLORS["text_main"],
            command=lambda _: self._on_sort_filter_change())
        self.filter_combo.set(self._filter_status)
        self.filter_combo.pack(side="right", padx=(4, 0))

        ctk.CTkLabel(toolbar, text="Filter:", font=FONTS["small"],
                     text_color=COLORS["text_dim"]).pack(side="right", padx=(0, 4))

        # ── Task cards container ──
        self.tasks_container = ctk.CTkFrame(section, fg_color="transparent")
        self.tasks_container.pack(fill="x", padx=10, pady=(5, 12))
        self.tasks_container.grid_columnconfigure(0, weight=1)

        self._render_sorted_filtered_tasks(all_tasks, today)

    def _on_sort_filter_change(self):
        """Re-render tasks when sort or filter changes."""
        self._filter_status = self.filter_combo.get()
        today = datetime.now().date()
        self._render_sorted_filtered_tasks(self.current_tasks, today)

    def _render_sorted_filtered_tasks(self, all_tasks, today):
        for w in self.tasks_container.winfo_children():
            w.destroy()
        self.status_vars.clear()
        self.modified_task_info.clear()

        # 1. Filter
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
        else:  # All
            tasks = list(all_tasks)

        # 2. Sort
        sort_val = self.sort_combo.get() if hasattr(self, "sort_combo") else "Deadline ↑ (soonest)"
        far_future = datetime(2099, 12, 31).date()
        far_past = datetime(2000, 1, 1).date()

        if "Deadline ↑" in sort_val:
            tasks.sort(key=lambda t: t._effective_deadline_date or far_future)
        elif "Deadline ↓" in sort_val:
            tasks.sort(key=lambda t: t._effective_deadline_date or far_past, reverse=True)
        elif "Priority" in sort_val:
            prio_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
            tasks.sort(key=lambda t: prio_order.get(t.priority.lower(), 9))
        elif "Assigned" in sort_val:
            tasks.sort(key=lambda t: _parse_deadline(t.date) or far_past)

        if not tasks:
            ctk.CTkLabel(self.tasks_container, text="No tasks match the current filter.",
                         font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=20)
            return

        for idx, task in enumerate(tasks):
            self._build_task_row(idx, task, today)

    def _build_task_row(self, idx, task, today):
        row = ctk.CTkFrame(self.tasks_container, fg_color=COLORS["input_bg"],
                           border_color=COLORS["border"], border_width=1, corner_radius=6)
        row.grid(row=idx, column=0, sticky="ew", pady=4, padx=4)
        row.grid_columnconfigure(0, weight=1)

        def bind_double_click(widget, t=task):
            widget.bind("<Double-1>", lambda event, tk=t: self.show_task_details_dialog(tk))
        bind_double_click(row)

        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w", padx=10, pady=10)
        bind_double_click(info_frame)

        # Task ID + description
        lbl_desc = ctk.CTkLabel(info_frame, text=f"[{task.task_id}] {task.description}",
                                font=FONTS["body_bold"], text_color=COLORS["text_main"],
                                justify="left", wraplength=700)
        lbl_desc.pack(anchor="w")
        bind_double_click(lbl_desc)

        # Dates row
        eff_dl = task._effective_deadline
        dl_str = format_date(eff_dl)
        if task._is_extended:
            dl_str += " (Extended)"

        dates_str = f"Assigned: {format_date(task.date)}  |  Deadline: {dl_str}"
        if task.priority.lower() in ("high", "urgent"):
            dates_str += f"  |  Priority: {task.priority}"
        lbl_dates = ctk.CTkLabel(info_frame, text=dates_str, font=FONTS["small"],
                                 text_color=COLORS["text_dim"])
        lbl_dates.pack(anchor="w", pady=(4, 0))
        bind_double_click(lbl_dates)

        # Overdue warning
        if task._effective_deadline_date:
            days_past = (today - task._effective_deadline_date).days
            if days_past > 0:
                lbl_timer = ctk.CTkLabel(info_frame,
                                         text=f"⚠ {days_past} days past deadline!",
                                         font=FONTS["small"], text_color=COLORS["error"])
                lbl_timer.pack(anchor="w")
                bind_double_click(lbl_timer)
            elif days_past == 0:
                lbl_timer = ctk.CTkLabel(info_frame, text="📌 Due today",
                                         font=FONTS["small"], text_color=COLORS["warning"])
                lbl_timer.pack(anchor="w")
                bind_double_click(lbl_timer)

        # Status combo
        var = ctk.StringVar(value=task.status)
        self.status_vars[task.task_id] = var

        def on_status_change(new_val, t=task, v=var):
            if new_val == "Delayed":
                self.prompt_extension_request(t, v)
            else:
                if t.task_id in self.modified_task_info:
                    del self.modified_task_info[t.task_id]

        combo = ctk.CTkComboBox(
            row, values=["Pending", "Delayed", "Completed"],
            variable=var, width=220, height=44,
            font=FONTS["body_bold"], dropdown_font=FONTS["body"],
            corner_radius=8, fg_color="#ffffff", border_color="#cbd5e1", border_width=1,
            button_color="#64748b", button_hover_color="#475569",
            dropdown_hover_color="#f1f5f9", dropdown_fg_color="#ffffff",
            dropdown_text_color=COLORS["text_main"], text_color=COLORS["text_main"],
            command=on_status_change)
        combo.grid(row=0, column=1, padx=15, pady=10)

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
        dialog.geometry("480x540")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (480 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (540 // 2)
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
                     font=FONTS["small"], text_color=COLORS["warning"]).pack(padx=20, pady=(0, 10), anchor="w")

        def submit():
            reason = reason_text.get("1.0", "end").strip()
            new_deadline = deadline_entry.get()
            if not reason:
                messagebox.showwarning("Missing Info", "Please provide a reason for the extension.")
                return
            person_name = self.current_user
            req_id = submit_extension_request(
                task_id=task.task_id, task_description=task.description,
                employee_name=person_name, current_deadline=task.deadline,
                requested_deadline=new_deadline, reason=reason,
                department=self.current_dept or "")
            self.modified_task_info[task.task_id] = {
                "reason": f"{reason} (Old Deadline: {task.deadline}) [Extension Request: {req_id}]",
                "deadline": task.deadline
            }
            dialog.destroy()
            messagebox.showinfo("Request Sent",
                                f"Extension request [{req_id}] has been submitted.\n"
                                "The manager will review it on the dashboard.")
            self._full_refresh()

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

    def _build_extension_section(self, ext_requests):
        section = ctk.CTkFrame(self.body_scroll, fg_color=COLORS["card_bg"],
                               corner_radius=8, border_width=1, border_color=COLORS["border"])
        section.pack(fill="x", pady=(10, 5), padx=2)

        hdr = ctk.CTkFrame(section, fg_color="transparent")
        hdr.pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(hdr, text="My Extension Requests", font=FONTS["subheader"],
                     text_color=COLORS["text_main"]).pack(side="left")
        ctk.CTkButton(hdr, text="↻ Refresh", width=80, font=FONTS["small"],
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      height=28, command=self._full_refresh).pack(side="right")

        if not ext_requests:
            ctk.CTkLabel(section, text="No extension requests yet.",
                         font=FONTS["small"], text_color=COLORS["text_dim"]).pack(pady=10)
            ctk.CTkFrame(section, fg_color="transparent", height=8).pack()
            return

        container = ctk.CTkFrame(section, fg_color="transparent")
        container.pack(fill="x", padx=10, pady=(5, 12))
        container.grid_columnconfigure(0, weight=1)

        for idx, req in enumerate(reversed(ext_requests)):
            status = req["status"]
            if status == "Pending":
                badge_color, badge_text = COLORS["warning"], "⏳ Pending"
            elif status == "Approved":
                badge_color, badge_text = COLORS["success"], "✓ Approved"
            else:
                badge_color, badge_text = COLORS["error"], "✗ Rejected"

            row = ctk.CTkFrame(container, fg_color=COLORS["input_bg"],
                               border_color=COLORS["border"], border_width=1, corner_radius=6)
            row.grid(row=idx * 2, column=0, sticky="ew", pady=3, padx=5)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(row, text=badge_text, font=FONTS["small"],
                         text_color="white", fg_color=badge_color,
                         corner_radius=4, width=90, height=24).grid(row=0, column=0, padx=(10, 5), pady=8)

            desc = req["task_description"]
            if len(desc) > 50:
                desc = desc[:50] + "..."
            ctk.CTkLabel(row, text=f"[{req['task_id']}] {desc}", font=FONTS["small"],
                         text_color=COLORS["text_main"]).grid(row=0, column=1, sticky="w", padx=5, pady=8)

            if status == "Approved":
                final_deadline = format_date(req.get("manager_deadline") or req["requested_deadline"])
                dl_text, dl_color = f"New Deadline: {final_deadline}", COLORS["success"]
            elif status == "Rejected":
                dl_text, dl_color = f"Deadline unchanged: {format_date(req['current_deadline'])}", COLORS["error"]
            else:
                dl_text, dl_color = f"Requested: {format_date(req['requested_deadline'])}", COLORS["text_dim"]

            ctk.CTkLabel(row, text=dl_text, font=FONTS["small"],
                         text_color=dl_color).grid(row=0, column=2, padx=(5, 10), pady=8)

            if status != "Pending" and req.get("manager_note"):
                note_row = ctk.CTkFrame(container, fg_color="transparent")
                note_row.grid(row=idx * 2 + 1, column=0, sticky="ew", padx=20, pady=(0, 3))
                ctk.CTkLabel(note_row, text=f"Manager note: {req['manager_note']}",
                             font=FONTS["small"], text_color=COLORS["text_dim"]).pack(anchor="w")

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
        prio_combo = ctk.CTkComboBox(row_prio, values=["Low", "Normal", "High", "Urgent"],
                                     width=200, height=36, font=FONTS["body"],
                                     dropdown_font=FONTS["body"], corner_radius=6,
                                     fg_color="#ffffff", border_color="#cbd5e1", border_width=1,
                                     button_color="#64748b", button_hover_color="#475569",
                                     dropdown_hover_color="#f1f5f9", dropdown_fg_color="#ffffff",
                                     dropdown_text_color=COLORS["text_main"], text_color=COLORS["text_main"])
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

    def submit_updates_only(self):
        modified_tasks = []
        for task in self.current_tasks:
            var = self.status_vars.get(task.task_id)
            if not var:
                continue
            new_status = var.get()
            if new_status != task.status:
                mod_info = self.modified_task_info.get(task.task_id, {})
                task_dict = {
                    "Task ID": task.task_id,
                    "Date": task.date,
                    "Task Description": task.description,
                    "Assigned To": task.assigned_to,
                    "Assigned By": task.assigned_by,
                    "Deadline": mod_info.get("deadline", task.deadline),
                    "Priority": task.priority,
                    "Status": new_status,
                    "Reason": mod_info.get("reason", task.reason),
                    "Source": task.source,
                    "Updated By": "UI Input",
                    "Last Updated": task.last_updated
                }
                modified_tasks.append(task_dict)

        if not modified_tasks:
            messagebox.showinfo("Info", "No task statuses were changed.")
            return

        self.btn_submit_updates.configure(state="disabled")
        try:
            success = self.n8n_client.submit_live_updates(modified_tasks)
            if success:
                messagebox.showinfo("Success", "Task statuses updated successfully.")
                recent_updates = load_recent_updates()
                for task_dict in modified_tasks:
                    recent_updates[task_dict["Task ID"]] = {
                        "status": task_dict["Status"],
                        "reason": task_dict.get("Reason", ""),
                        "timestamp": time.time()
                    }
                    for task in self.current_tasks:
                        if task.task_id == task_dict["Task ID"]:
                            task.status = task_dict["Status"]
                            if "Reason" in task_dict:
                                task.reason = task_dict["Reason"]
                            break
                save_recent_updates(recent_updates)
                self._full_refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update tasks:\n{e}")
        finally:
            self.btn_submit_updates.configure(state="normal")


if __name__ == "__main__":
    app = TaskUpdaterApp()
    app.mainloop()
