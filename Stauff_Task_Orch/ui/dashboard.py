import tkinter as tk
import customtkinter as ctk
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from .components import (KPICard, ChartCard, BG_COLOR, TEXT_COLOR,
                         FONT_H1, FONT_TITLE, CARD_BG, BORDER_COLOR, TEXT_MUTED,
                         CHART_COLORS, FONT_MAIN, FONT_BOLD, FONT_SMALL, TimelineTracker)
from data.repository import DataRepository
import config


# Status colours for charts
STATUS_COLORS = {
    "Pending": "#f59e0b",
    "Completed": "#10b981",
    "Delayed": "#ef4444",
    "Done": "#10b981",
}


def _parse_date(date_str: str):
    """Try parsing common date formats and return a datetime or None."""
    for fmt in ("%d/%m/%Y", "%d/%m", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _is_overdue(task) -> bool:
    """Return True if a task has a deadline today or in the past and is still pending."""
    if not task.due_date or task.status.lower() in ("completed", "done", "update"):
        return False
    dl = _parse_date(task.due_date)
    if dl is None:
        return False
    return dl.date() <= datetime.now().date()


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, repository: DataRepository, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self.repository = repository

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        lbl_title = ctk.CTkLabel(self.scroll, text="Executive Dashboard", font=FONT_H1, text_color=TEXT_COLOR)
        lbl_title.pack(anchor="w", padx=20, pady=(20, 5))

        self.lbl_status = ctk.CTkLabel(self.scroll, text="", font=("Inter", 10), text_color=TEXT_MUTED)
        self.lbl_status.pack(anchor="w", padx=20, pady=(0, 15))

        # Risk Summary
        self.risk_summary_frame = ctk.CTkFrame(self.scroll, fg_color="#fee2e2", corner_radius=8, border_width=1, border_color="#ef4444")
        self.risk_summary_frame.pack(fill="x", padx=20, pady=(0, 15))

        # KPI rows
        self.kpi_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.kpi_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Charts bottleneck row
        self.charts_row_bottleneck = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.charts_row_bottleneck.pack(fill="x", padx=20, pady=(0, 15))
        self.charts_row_bottleneck.grid_columnconfigure(0, weight=1)

        # Attention required row
        self.attention_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.attention_row.pack(fill="x", padx=20, pady=(0, 15))
        self.attention_row.grid_columnconfigure(0, weight=1)

        # Charts row 1
        self.charts_row1 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.charts_row1.pack(fill="x", padx=20, pady=(0, 15))
        self.charts_row1.grid_columnconfigure((0, 1), weight=1)

        # Charts row 2
        self.charts_row2 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.charts_row2.pack(fill="x", padx=20, pady=(0, 15))
        self.charts_row2.grid_columnconfigure((0, 1), weight=1)

        # Charts row 3
        self.charts_row3 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.charts_row3.pack(fill="x", padx=20, pady=(0, 20))
        self.charts_row3.grid_columnconfigure((0, 1), weight=1)

        self._last_data_sig = None
        self._last_status_text_prefix = ""
        self.build_content(force=True)

    def _navigate_to_filtered_tasks(self, filter_name):
        view = self.master.views.get("All Tasks")
        if view and hasattr(view, 'apply_preset_filter'):
            view.apply_preset_filter(filter_name)
        self.master.show_view("All Tasks")

    def build_content(self, force: bool = False):
        all_tasks = self.repository.get_tasks()
        all_goals = self.repository.get_goals()
        all_updates = self.repository.get_updates()
        all_people = self.repository.get_people()

        selected_dept = getattr(self.master, "current_dept", "All Departments")
        if hasattr(selected_dept, "get"):
            selected_dept = selected_dept.get()

        try:
            from services.extension_store import get_all_pending_requests
            pending_requests = len(get_all_pending_requests())
        except Exception:
            pending_requests = 0

        task_sigs = tuple((t.id, getattr(t, 'status', ''), getattr(t, 'due_date', ''), getattr(t, 'priority', '')) for t in all_tasks)
        goal_sigs = tuple((g.id, getattr(g, 'status', '')) for g in all_goals)
        data_sig = (
            selected_dept,
            len(all_tasks),
            task_sigs,
            len(all_goals),
            goal_sigs,
            len(all_updates),
            len(all_people),
            pending_requests,
        )

        if not force and self._last_data_sig == data_sig:
            if self._last_status_text_prefix:
                self.lbl_status.configure(
                    text=f"{self._last_status_text_prefix} · Last refreshed: {datetime.now().strftime('%H:%M:%S')}")
            return

        scroll_y = 0.0
        try:
            scroll_y = self.scroll._parent_canvas.yview()[0]
        except Exception:
            pass

        self._last_data_sig = data_sig

        # Clear all frames
        for frame in [getattr(self, "risk_summary_frame", None), self.kpi_frame, getattr(self, "charts_row_bottleneck", None),
                      getattr(self, "attention_row", None), self.charts_row1,
                      self.charts_row2, self.charts_row3]:
            if frame:
                self._clear_frame(frame)

        if selected_dept != "All Departments":
            tasks = [t for t in all_tasks if getattr(t, 'department', '') == selected_dept]
            goals = [g for g in all_goals if getattr(g, 'department', '') == selected_dept]
            updates = [u for u in all_updates if getattr(u, 'department', '') == selected_dept]
            people = [p for p in all_people if getattr(p, 'department', '') == selected_dept]
        else:
            tasks = all_tasks
            goals = all_goals
            updates = all_updates
            people = all_people

        total_tasks = len(tasks)
        total_goals = len(goals)
        total_updates = len(updates)
        total_people = len(people)

        weekly_goals = sum(1 for g in goals if g.timeframe == "Weekly")
        monthly_goals = sum(1 for g in goals if g.timeframe == "Monthly")

        # Status breakdowns
        task_status = Counter(t.status.strip().capitalize() for t in tasks)
        completed_tasks = task_status.get("Completed", 0) + task_status.get("Done", 0) + task_status.get("Update", 0)
        pending_tasks = task_status.get("Pending", 0)
        delayed_tasks = task_status.get("Delayed", 0)
        overdue_tasks = sum(1 for t in tasks if _is_overdue(t))

        completion_rate = round(completed_tasks / total_tasks * 100) if total_tasks else 0

        goal_status = Counter(g.status.strip().capitalize() for g in goals)
        completed_goals = goal_status.get("Completed", 0) + goal_status.get("Done", 0) + goal_status.get("Update", 0)
        goal_completion_rate = round(completed_goals / total_goals * 100) if total_goals else 0

        # ── KPI Row 1 ──
        import sys, os
        from data.repository import TEAM_STRUCTURE
        try:
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from services.extension_store import get_all_pending_requests
            pending_requests = len(get_all_pending_requests())
        except ImportError:
            pending_requests = 0

        critical_tasks = sum(1 for t in tasks if t.priority.strip().lower() in ("high", "critical") and t.status.strip().lower() not in ("completed", "done", "update"))
        at_risk_tasks = delayed_tasks
        team_load = round(total_tasks / total_people, 1) if total_people else 0

        # Build Risk Summary
        dept_risks = defaultdict(int)
        for t in all_tasks:
            if t.status.lower() == "delayed" or _is_overdue(t) or (t.priority.strip().lower() in ("high", "critical") and t.status.lower() not in ("completed", "done", "update")):
                dept_risks[t.department] += 1
        
        at_risk_depts = [f"{d} ({c})" for d, c in dept_risks.items() if c > 0]
        risk_text = f"Departments at Risk: {', '.join(at_risk_depts) if at_risk_depts else 'None'}"
        
        lbl_risk = ctk.CTkLabel(self.risk_summary_frame, text="⚠️ Risk Overview", font=FONT_TITLE, text_color="#b91c1c")
        lbl_risk.pack(anchor="w", padx=15, pady=(15, 5))
        
        lbl_risk_depts = ctk.CTkLabel(self.risk_summary_frame, text=risk_text, font=FONT_MAIN, text_color="#991b1b")
        lbl_risk_depts.pack(anchor="w", padx=15, pady=0)
        
        lbl_risk_counts = ctk.CTkLabel(self.risk_summary_frame, text=f"Critical Tasks: {critical_tasks}  |  At-Risk Tasks: {at_risk_tasks}  |  Pending Decisions (Extensions): {pending_requests}", font=FONT_BOLD, text_color="#991b1b")
        lbl_risk_counts.pack(anchor="w", padx=15, pady=(5, 15))

        self.kpi_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        KPICard(self.kpi_frame, "Critical Issues", str(critical_tasks),
                subtitle="high priority", clickable=True, command=lambda: self._navigate_to_filtered_tasks("Critical Issues")).grid(row=0, column=0, padx=6, pady=5, sticky="ew")
        KPICard(self.kpi_frame, "Overdue", str(overdue_tasks),
                subtitle="past deadline", clickable=True, command=lambda: self._navigate_to_filtered_tasks("Overdue")).grid(row=0, column=1, padx=6, pady=5, sticky="ew")
        KPICard(self.kpi_frame, "At risk", str(at_risk_tasks),
                subtitle="delayed tasks", clickable=True, command=lambda: self._navigate_to_filtered_tasks("At risk")).grid(row=0, column=2, padx=6, pady=5, sticky="ew")
        KPICard(self.kpi_frame, "Team Load", str(team_load),
                subtitle="avg tasks/person", clickable=True, command=lambda: self.master.show_view("Analytics")).grid(row=0, column=3, padx=6, pady=5, sticky="ew")
        KPICard(self.kpi_frame, "Approvals", str(pending_requests),
                subtitle="pending extensions", clickable=True, command=lambda: self.master.show_view("Extension Requests")).grid(row=0, column=4, padx=6, pady=5, sticky="ew")
        KPICard(self.kpi_frame, "Progress", f"{completion_rate}%",
                subtitle="completion rate", clickable=True, command=lambda: self.master.show_view("Goals")).grid(row=0, column=5, padx=6, pady=5, sticky="ew")

        # ── Bottlenecks Tracker (Timeline) ──
        tracker_data = []
        for dept in TEAM_STRUCTURE.keys():
            b_count = dept_risks.get(dept, 0)
            status = "red" if b_count > 0 else "green"
            if b_count == 1:
                desc = "1 bottleneck"
            elif b_count > 1:
                desc = f"{b_count} bottlenecks"
            else:
                desc = "On Track"
            tracker_data.append({"name": dept, "status": status, "desc": desc})
            
        timeline = TimelineTracker(self.charts_row_bottleneck, tracker_data)
        timeline.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")

        # ── Attention Required Widget ──
        attention_frame = ctk.CTkFrame(self.attention_row, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=BORDER_COLOR) 
        attention_frame.pack(fill="x", padx=8, pady=5)
        
        hdr = ctk.CTkFrame(attention_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=15, pady=(15, 5))
        
        lbl_att = ctk.CTkLabel(hdr, text="⚠️ ATTENTION REQUIRED", font=FONT_TITLE, text_color="#eab308")
        lbl_att.pack(side="left", padx=(0, 10))
        
        attention_tasks = [t for t in tasks if t.status.lower() == "delayed" or _is_overdue(t) or (t.priority.strip().lower() in ("high", "critical") and t.status.lower() not in ("completed", "done", "update"))]
        
        num_items = len(attention_tasks)
        num_crit = sum(1 for t in attention_tasks if t.priority.strip().lower() in ("high", "critical"))
        num_blocked = sum(1 for t in attention_tasks if t.status.strip().lower() == "delayed")
        
        badge_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        badge_frame.pack(side="left")
        
        def _make_badge(parent, text, command=None):
            b = ctk.CTkFrame(parent, fg_color="#f1f5f9", corner_radius=6, border_width=1, border_color=BORDER_COLOR)
            b.pack(side="left", padx=4)
            lbl = ctk.CTkLabel(b, text=text, font=FONT_SMALL, text_color=TEXT_COLOR)
            lbl.pack(padx=8, pady=2)
            if command:
                b.configure(cursor="hand2")
                b.bind("<Button-1>", lambda e: command())
                lbl.bind("<Button-1>", lambda e: command())
            
        _make_badge(badge_frame, f"{num_items} items require attention", command=lambda: self._navigate_to_filtered_tasks("Attention Required"))
        _make_badge(badge_frame, f"{num_crit} critical", command=lambda: self._navigate_to_filtered_tasks("Critical Issues"))
        _make_badge(badge_frame, f"{num_blocked} blocked", command=lambda: self._navigate_to_filtered_tasks("At risk"))
        _make_badge(badge_frame, f"{pending_requests} pending decisions", command=lambda: self.master.show_view("Extension Requests"))
        
        tbl_frame = ctk.CTkFrame(attention_frame, fg_color="transparent")
        tbl_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        cols = ["Priority", "Issue", "Impact", "Owner", "Due"]
        for i, col in enumerate(cols):
            ctk.CTkLabel(tbl_frame, text=col, font=FONT_BOLD, text_color=TEXT_COLOR).grid(row=0, column=i, sticky="w", padx=10, pady=(5, 10))
            tbl_frame.grid_columnconfigure(i, weight=1 if i == 1 else 0)
            
        ctk.CTkFrame(tbl_frame, height=1, fg_color=BORDER_COLOR).grid(row=1, column=0, columnspan=5, sticky="ew")
        
        for idx, t in enumerate(attention_tasks[:5]):
            row = idx * 2 + 2
            prio = t.priority.strip().capitalize()
            prio_color = "#ef4444" if prio in ("High", "Critical") else "#f97316"
            
            p_frame = ctk.CTkFrame(tbl_frame, fg_color="transparent")
            p_frame.grid(row=row, column=0, sticky="w", padx=10, pady=10)
            
            canvas = tk.Canvas(p_frame, width=12, height=12, bg=CARD_BG, highlightthickness=0)
            canvas.pack(side="left", padx=(0, 6))
            canvas.create_oval(2, 2, 10, 10, fill=prio_color, outline="")
            
            ctk.CTkLabel(p_frame, text=prio, font=FONT_MAIN, text_color=TEXT_COLOR).pack(side="left")
            
            # Use wraplength instead of truncating so no text is cut off
            ctk.CTkLabel(tbl_frame, text=t.task, font=FONT_MAIN, text_color=TEXT_COLOR, justify="left", anchor="w", wraplength=450).grid(row=row, column=1, sticky="w", padx=10, pady=10)
            
            impact = "Blocked" if t.status.lower() == "delayed" else "At Risk"
            ctk.CTkLabel(tbl_frame, text=impact, font=FONT_MAIN, text_color=TEXT_COLOR).grid(row=row, column=2, sticky="w", padx=10, pady=10)
            
            ctk.CTkLabel(tbl_frame, text=t.person, font=FONT_MAIN, text_color=TEXT_COLOR).grid(row=row, column=3, sticky="w", padx=10, pady=10)
            
            due = t.due_date if t.due_date else "N/A"
            ctk.CTkLabel(tbl_frame, text=due, font=FONT_MAIN, text_color=TEXT_COLOR).grid(row=row, column=4, sticky="w", padx=10, pady=10)
            
            ctk.CTkFrame(tbl_frame, height=1, fg_color=BORDER_COLOR).grid(row=row+1, column=0, columnspan=5, sticky="ew")

        # ── Chart Row 1: Task Status & Priority ──
        # Overall task status donut
        chart_pie = ChartCard(self.charts_row1, "Overall Task Status", fig_width=5, fig_height=2.8)
        chart_pie.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")
        if task_status:
            merged = defaultdict(int)
            for st, cnt in task_status.items():
                if st.lower() in ("done", "completed", "update"):
                    merged["Completed"] += cnt
                else:
                    merged[st] += cnt
            labels = []
            vals = []
            pie_colors = []
            for st_name in ["Completed", "Pending", "Delayed"]:
                if st_name in merged:
                    labels.append(st_name)
                    vals.append(merged[st_name])
                    pie_colors.append(STATUS_COLORS[st_name])
            for st_name, cnt in merged.items():
                if st_name not in ["Completed", "Pending", "Delayed"]:
                    labels.append(st_name)
                    vals.append(cnt)
                    pie_colors.append(CHART_COLORS[len(labels) % len(CHART_COLORS)])
            chart_pie.pie_chart(labels, vals, colors=pie_colors)

        # Priority distribution donut
        chart_priority = ChartCard(self.charts_row1, "Task Priority Distribution", fig_width=5, fig_height=2.8)
        chart_priority.grid(row=0, column=1, padx=8, pady=5, sticky="nsew")
        priority_counts = Counter(t.priority.strip().capitalize() if t.priority.strip() else "Normal" for t in tasks)
        if priority_counts:
            priority_order = ["High", "Normal", "Low"]
            priority_colors = {"High": "#ef4444", "Normal": "#0ea5e9", "Low": "#10b981"}
            labels = [p for p in priority_order if p in priority_counts]
            labels += [p for p in priority_counts if p not in priority_order]
            vals = [priority_counts[l] for l in labels]
            colors = [priority_colors.get(l, CHART_COLORS[0]) for l in labels]
            chart_priority.pie_chart(labels, vals, colors=colors)

        # ── Chart Row 2: Strategic Goals & Deadline Compliance ──
        # Goals by timeframe & status donut
        chart_goal_dept = ChartCard(self.charts_row2, "Strategic Goals Breakdown", fig_width=5, fig_height=2.8)
        chart_goal_dept.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")
        timeframe_counts = Counter(g.timeframe.strip().capitalize() if getattr(g, 'timeframe', '') else "Other" for g in goals)
        if timeframe_counts:
            tf_labels = list(timeframe_counts.keys())
            tf_vals = [timeframe_counts[l] for l in tf_labels]
            tf_colors = ["#6366f1", "#0ea5e9", "#f59e0b", "#10b981"][:len(tf_labels)]
            chart_goal_dept.pie_chart(tf_labels, tf_vals, colors=tf_colors)
        else:
            dept_goal_counts = Counter(g.department for g in all_goals if g.department)
            if dept_goal_counts:
                chart_goal_dept.pie_chart(list(dept_goal_counts.keys()), list(dept_goal_counts.values()))

        # Company-wide Deadline Health & Compliance (Modern Donut)
        chart_dl = ChartCard(self.charts_row2, "Deadline Health & Compliance", fig_width=5, fig_height=2.8)
        chart_dl.grid(row=0, column=1, padx=8, pady=5, sticky="nsew")
        comp_completed = completed_tasks
        comp_overdue = overdue_tasks + delayed_tasks
        comp_on_track = 0
        comp_no_dl = 0
        for t in tasks:
            if t.status.strip().lower() in ("completed", "done", "update"):
                continue
            if not getattr(t, 'due_date', '').strip():
                comp_no_dl += 1
            elif not _is_overdue(t) and t.status.strip().lower() != "delayed":
                comp_on_track += 1

        compliance_labels = ["Completed", "On Track", "Overdue / Delayed", "No Deadline"]
        compliance_vals = [comp_completed, comp_on_track, comp_overdue, comp_no_dl]
        compliance_colors = ["#10b981", "#0ea5e9", "#ef4444", "#94a3b8"]
        filtered = [(l, v, c) for l, v, c in zip(compliance_labels, compliance_vals, compliance_colors) if v > 0]
        if filtered:
            chart_dl.pie_chart([f[0] for f in filtered], [f[1] for f in filtered], colors=[f[2] for f in filtered])
        else:
            chart_dl.ax.text(0.5, 0.5, "No task data", ha="center", va="center", color=TEXT_MUTED, transform=chart_dl.ax.transAxes)
            chart_dl.draw()

        # ── Chart Row 3: Activity Trends & Daily Updates Over Time ──
        show_updates = getattr(config, "SHOW_DAILY_UPDATES", False)
        # Task activity over time (Smooth area line chart)
        chart_timeline = ChartCard(self.charts_row3, "Task Creation Trend", fig_width=5 if show_updates else 10, fig_height=2.8)
        if show_updates:
            chart_timeline.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")
        else:
            chart_timeline.grid(row=0, column=0, columnspan=2, padx=8, pady=5, sticky="nsew")
        date_task = defaultdict(int)
        for t in tasks:
            if getattr(t, 'date', '').strip():
                date_task[t.date.strip()] += 1
        if date_task:
            sorted_dates = sorted(date_task.keys())[-14:] # Show recent 14 active days
            chart_timeline.line_chart(sorted_dates, {"Tasks Created": [date_task[d] for d in sorted_dates]})
        else:
            chart_timeline.ax.text(0.5, 0.5, "No task activity recorded", ha="center", va="center", color=TEXT_MUTED, transform=chart_timeline.ax.transAxes)
            chart_timeline.draw()

        if show_updates:
            # Updates over time (Smooth area line chart)
            chart_updates = ChartCard(self.charts_row3, "Daily Updates Activity", fig_width=5, fig_height=2.8)
            chart_updates.grid(row=0, column=1, padx=8, pady=5, sticky="nsew")
            date_update = defaultdict(int)
            for u in updates:
                if getattr(u, 'date', '').strip():
                    date_update[u.date.strip()] += 1
            if date_update:
                sorted_dates = sorted(date_update.keys())[-14:] # Show recent 14 active days
                chart_updates.line_chart(sorted_dates, {"Updates Submitted": [date_update[d] for d in sorted_dates]})
            else:
                chart_updates.ax.text(0.5, 0.5, "No update activity recorded", ha="center", va="center", color=TEXT_MUTED, transform=chart_updates.ax.transAxes)
                chart_updates.draw()

        # Status bar text
        updates_status_str = f" · {total_updates} updates" if show_updates else ""
        self._last_status_text_prefix = (
            f"📊 {total_tasks} tasks · {total_goals} goals{updates_status_str} · "
            f"{completed_tasks} completed · {overdue_tasks} overdue"
        )
        self.lbl_status.configure(
            text=f"{self._last_status_text_prefix} · Last refreshed: {datetime.now().strftime('%H:%M:%S')}")

        def _restore():
            try:
                self.scroll._parent_canvas.yview_moveto(scroll_y)
            except Exception:
                pass
        self.after_idle(_restore)
        self.after(60, _restore)

    def refresh_data(self):
        """Called after live data refresh."""
        self.build_content(force=False)

    @staticmethod
    def _clear_frame(frame):
        for w in frame.winfo_children():
            w.destroy()
