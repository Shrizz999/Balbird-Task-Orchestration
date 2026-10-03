import tkinter as tk
import customtkinter as ctk
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from .components import (KPICard, ChartCard, BG_COLOR, TEXT_COLOR,
                         FONT_H1, FONT_TITLE, CARD_BG, BORDER_COLOR, TEXT_MUTED,
                         CHART_COLORS, FONT_MAIN, FONT_BOLD, FONT_SMALL, TimelineTracker)
from data.repository import DataRepository


# Status colours for charts
STATUS_COLORS = {
    "Pending": "#f59e0b",
    "Completed": "#10b981",
    "Delayed": "#ef4444",
    "Done": "#10b981",
}


def _parse_date(date_str: str):
    """Try parsing common date formats and return a datetime or None."""
    for fmt in ("%d/%m/%Y", "%d/%m", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _is_overdue(task) -> bool:
    """Return True if a task has a deadline in the past and is still pending."""
    if not task.due_date or task.status.lower() in ("completed", "done"):
        return False
    dl = _parse_date(task.due_date)
    if dl is None:
        return False
    return dl.date() < datetime.now().date()


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
        self.charts_row3.pack(fill="x", padx=20, pady=(0, 15))
        self.charts_row3.grid_columnconfigure((0, 1), weight=1)

        # Charts row 4
        self.charts_row4 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.charts_row4.pack(fill="x", padx=20, pady=(0, 15))
        self.charts_row4.grid_columnconfigure((0, 1), weight=1)

        # Charts row 5
        self.charts_row5 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.charts_row5.pack(fill="x", padx=20, pady=(0, 20))
        self.charts_row5.grid_columnconfigure((0, 1), weight=1)

        self.build_content()

    def _navigate_to_filtered_tasks(self, filter_name):
        view = self.master.views.get("All Tasks")
        if view and hasattr(view, 'apply_preset_filter'):
            view.apply_preset_filter(filter_name)
        self.master.show_view("All Tasks")

    def build_content(self):
        # Clear all frames
        for frame in [getattr(self, "risk_summary_frame", None), self.kpi_frame, getattr(self, "charts_row_bottleneck", None),
                      getattr(self, "attention_row", None), self.charts_row1,
                      self.charts_row2, self.charts_row3, self.charts_row4, self.charts_row5]:
            if frame:
                self._clear_frame(frame)

        all_tasks = self.repository.get_tasks()
        all_goals = self.repository.get_goals()
        all_updates = self.repository.get_updates()
        all_people = self.repository.get_people()

        selected_dept = getattr(self.master, "current_dept", "All Departments")
        if hasattr(selected_dept, "get"):
            selected_dept = selected_dept.get()

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
        completed_tasks = task_status.get("Completed", 0) + task_status.get("Done", 0)
        pending_tasks = task_status.get("Pending", 0)
        delayed_tasks = task_status.get("Delayed", 0)
        overdue_tasks = sum(1 for t in tasks if _is_overdue(t))

        completion_rate = round(completed_tasks / total_tasks * 100) if total_tasks else 0

        goal_status = Counter(g.status.strip().capitalize() for g in goals)
        completed_goals = goal_status.get("Completed", 0) + goal_status.get("Done", 0)
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

        critical_tasks = sum(1 for t in tasks if t.priority.strip().lower() in ("high", "critical") and t.status.strip().lower() not in ("completed", "done"))
        at_risk_tasks = delayed_tasks
        team_load = round(total_tasks / total_people, 1) if total_people else 0

        # Build Risk Summary
        dept_risks = defaultdict(int)
        for t in all_tasks:
            if t.status.lower() == "delayed" or _is_overdue(t) or (t.priority.strip().lower() in ("high", "critical") and t.status.lower() not in ("completed", "done")):
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
                desc = "Smooth sailing"
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
        
        attention_tasks = [t for t in tasks if t.status.lower() == "delayed" or _is_overdue(t) or (t.priority.strip().lower() in ("high", "critical") and t.status.lower() not in ("completed", "done"))]
        
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

        # ── Chart Row 1: Status overview ──
        # Task status breakdown (stacked per person)
        chart_status = ChartCard(self.charts_row1, "Task Status by Person", fig_width=5, fig_height=2.8)
        chart_status.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")
        person_names = sorted(set(t.person for t in tasks if t.person))
        if person_names:
            status_types = ["Pending", "Completed", "Delayed"]
            status_data = {}
            for st in status_types:
                status_data[st] = []
                for p in person_names:
                    count = sum(1 for t in tasks if t.person == p and t.status.strip().capitalize() == st)
                    status_data[st].append(count)
            # Also count "Done" as "Completed"
            for i, p in enumerate(person_names):
                status_data["Completed"][i] += sum(1 for t in tasks if t.person == p and t.status.strip().lower() == "done")
            chart_status.stacked_bar_chart(person_names, status_data,
                                           colors=[STATUS_COLORS["Pending"], STATUS_COLORS["Completed"], STATUS_COLORS["Delayed"]])

        # Overall task status pie
        chart_pie = ChartCard(self.charts_row1, "Overall Task Status", fig_width=5, fig_height=2.8)
        chart_pie.grid(row=0, column=1, padx=8, pady=5, sticky="nsew")
        if task_status:
            merged = defaultdict(int)
            for st, cnt in task_status.items():
                if st.lower() in ("done", "completed"):
                    merged["Completed"] += cnt
                else:
                    merged[st] += cnt
            labels = list(merged.keys())
            vals = list(merged.values())
            pie_colors = [STATUS_COLORS.get(l, CHART_COLORS[i % len(CHART_COLORS)]) for i, l in enumerate(labels)]
            chart_pie.pie_chart(labels, vals, colors=pie_colors)

        # ── Chart Row 2: Deadlines & Overdue ──
        # Overdue per person
        chart_overdue = ChartCard(self.charts_row2, "Overdue Tasks by Person", fig_width=5, fig_height=2.8)
        chart_overdue.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")
        overdue_per_person = Counter(t.person for t in tasks if _is_overdue(t))
        if overdue_per_person:
            labels = list(overdue_per_person.keys())
            vals = list(overdue_per_person.values())
            chart_overdue.bar_chart(labels, vals, color=["#ef4444"] * len(labels))
        else:
            chart_overdue.ax.text(0.5, 0.5, "No overdue tasks! 🎉", transform=chart_overdue.ax.transAxes,
                                  ha="center", va="center", fontsize=12, color="#10b981")
            chart_overdue.draw()

        # Priority distribution
        chart_priority = ChartCard(self.charts_row2, "Task Priority Distribution", fig_width=5, fig_height=2.8)
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

        # ── Chart Row 3: Goal insights ──
        # Goal status per person (stacked)
        chart_goal_status = ChartCard(self.charts_row3, "Goal Status by Person", fig_width=5, fig_height=2.8)
        chart_goal_status.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")
        goal_persons = sorted(set(g.person for g in goals if g.person))
        if goal_persons:
            goal_status_types = ["Pending", "Completed", "Delayed"]
            goal_data = {}
            for st in goal_status_types:
                goal_data[st] = []
                for p in goal_persons:
                    count = sum(1 for g in goals if g.person == p and g.status.strip().capitalize() == st)
                    goal_data[st].append(count)
            for i, p in enumerate(goal_persons):
                goal_data["Completed"][i] += sum(1 for g in goals if g.person == p and g.status.strip().lower() == "done")
            chart_goal_status.stacked_bar_chart(goal_persons, goal_data,
                                                 colors=[STATUS_COLORS["Pending"], STATUS_COLORS["Completed"], STATUS_COLORS["Delayed"]])

        # Goals per department
        chart_goal_dept = ChartCard(self.charts_row3, "Goals per Department", fig_width=5, fig_height=2.8)
        chart_goal_dept.grid(row=0, column=1, padx=8, pady=5, sticky="nsew")
        dept_goal_counts = Counter(g.department for g in all_goals if g.department)
        if dept_goal_counts:
            chart_goal_dept.pie_chart(list(dept_goal_counts.keys()), list(dept_goal_counts.values()))

        # ── Chart Row 4: Time series ──
        # Task activity over time
        chart_timeline = ChartCard(self.charts_row4, "Task Activity Over Time", fig_width=5, fig_height=2.8)
        chart_timeline.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")
        date_task = defaultdict(int)
        for t in tasks:
            date_task[t.date] += 1
        if date_task:
            sorted_dates = sorted(date_task.keys())
            chart_timeline.line_chart(sorted_dates, {"Tasks": [date_task[d] for d in sorted_dates]})

        # Updates over time
        chart_updates = ChartCard(self.charts_row4, "Update Activity Over Time", fig_width=5, fig_height=2.8)
        chart_updates.grid(row=0, column=1, padx=8, pady=5, sticky="nsew")
        date_update = defaultdict(int)
        for u in updates:
            date_update[u.date] += 1
        if date_update:
            sorted_dates = sorted(date_update.keys())
            chart_updates.line_chart(sorted_dates, {"Updates": [date_update[d] for d in sorted_dates]})

        # ── Chart Row 5: Workload & Source ──
        # Workload heatmap (tasks per person stacked by source)
        chart_source = ChartCard(self.charts_row5, "Tasks by Source", fig_width=5, fig_height=2.8)
        chart_source.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")
        source_counts = Counter(t.source.strip() if t.source.strip() else "Unknown" for t in tasks)
        if source_counts:
            labels = list(source_counts.keys())
            vals = list(source_counts.values())
            chart_source.bar_chart(labels, vals, color=CHART_COLORS[:len(labels)])

        # Deadline compliance: tasks with vs without deadlines per person
        chart_dl = ChartCard(self.charts_row5, "Deadline Coverage by Person", fig_width=5, fig_height=2.8)
        chart_dl.grid(row=0, column=1, padx=8, pady=5, sticky="nsew")
        if person_names:
            with_dl = []
            without_dl = []
            for p in person_names:
                p_tasks = [t for t in tasks if t.person == p]
                with_dl.append(sum(1 for t in p_tasks if t.due_date.strip()))
                without_dl.append(sum(1 for t in p_tasks if not t.due_date.strip()))
            chart_dl.stacked_bar_chart(person_names,
                                        {"With Deadline": with_dl, "No Deadline": without_dl},
                                        colors=["#10b981", "#e2e8f0"])

        # Status bar text
        self.lbl_status.configure(
            text=f"📊 {total_tasks} tasks · {total_goals} goals · {total_updates} updates · "
                 f"{completed_tasks} completed · {overdue_tasks} overdue · Last refreshed: {datetime.now().strftime('%H:%M:%S')}")

    def refresh_data(self):
        """Called after live data refresh."""
        self.build_content()

    @staticmethod
    def _clear_frame(frame):
        for w in frame.winfo_children():
            w.destroy()
