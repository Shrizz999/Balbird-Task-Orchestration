import re
import customtkinter as ctk
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any

from .components import (
    KPICard, ChartCard, ModernCardTable, BG_COLOR, TEXT_COLOR,
    FONT_H1, FONT_TITLE, FONT_BOLD, FONT_MAIN, FONT_SMALL,
    CARD_BG, BORDER_COLOR, TEXT_MUTED, CHART_COLORS
)
from data.repository import DataRepository, TEAM_STRUCTURE


def _parse_date(date_str: str):
    for fmt in ("%d/%m/%Y", "%d/%m", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _is_overdue(task) -> bool:
    if not getattr(task, 'due_date', '') or task.status.lower() in ("completed", "done", "update"):
        return False
    dl = _parse_date(task.due_date)
    if dl is None:
        return False
    return dl.date() <= datetime.now().date()


STATUS_COLORS = {
    "Pending": "#f59e0b",
    "Completed": "#10b981",
    "Delayed": "#ef4444",
    "Done": "#10b981",
}


class DepartmentsView(ctk.CTkFrame):
    """Department Hub: Dedicated dashboard for each department with KPIs, charts, and tables."""

    def __init__(self, master, repository: DataRepository, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self.repository = repository
        self.departments = self._get_department_list()
        self.current_dept_name = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_main_area()

        if self.departments:
            self._select_department(self.departments[0])

    def _get_department_list(self) -> List[str]:
        all_tasks = self.repository.get_tasks()
        all_goals = self.repository.get_goals()
        all_people = self.repository.get_people()

        dept_set = set(TEAM_STRUCTURE.keys())
        for t in all_tasks:
            if getattr(t, 'department', '').strip():
                dept_set.add(t.department.strip())
        for g in all_goals:
            if getattr(g, 'department', '').strip():
                dept_set.add(g.department.strip())
        for p in all_people:
            if getattr(p, 'department', '').strip():
                dept_set.add(p.department.strip())

        # Keep canonical team structure first, then any additional
        ordered = [d for d in TEAM_STRUCTURE.keys() if d in dept_set]
        ordered += sorted([d for d in dept_set if d not in TEAM_STRUCTURE.keys()])
        return ordered if ordered else ["General"]

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=CARD_BG, border_width=1,
                                    border_color=BORDER_COLOR, corner_radius=0, width=220)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        lbl_title = ctk.CTkLabel(self.sidebar, text="Departments", font=FONT_TITLE, text_color=TEXT_COLOR)
        lbl_title.pack(anchor="w", padx=16, pady=(20, 4))

        lbl_sub = ctk.CTkLabel(self.sidebar, text="Select department to inspect", font=FONT_SMALL, text_color=TEXT_MUTED)
        lbl_sub.pack(anchor="w", padx=16, pady=(0, 15))

        self.scroll_buttons = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_buttons.pack(fill="both", expand=True, padx=6, pady=(0, 10))

        self.dept_buttons = []
        for dept in self.departments:
            btn = ctk.CTkButton(
                self.scroll_buttons,
                text=dept,
                fg_color="transparent",
                text_color=TEXT_COLOR,
                hover_color=BG_COLOR,
                anchor="w",
                font=("Inter", 12),
                height=34,
                command=lambda d=dept: self._select_department(d)
            )
            btn.pack(fill="x", padx=4, pady=2)
            self.dept_buttons.append((dept, btn))

    def _build_main_area(self):
        self.main_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", pady=10, padx=(0, 10))

        # ── Header ──
        self.lbl_name = ctk.CTkLabel(self.main_area, text="", font=FONT_H1, text_color=TEXT_COLOR)
        self.lbl_name.pack(anchor="w", padx=10, pady=(0, 2))

        self.lbl_dept_info = ctk.CTkLabel(self.main_area, text="", font=("Inter", 12), text_color=TEXT_MUTED)
        self.lbl_dept_info.pack(anchor="w", padx=10, pady=(0, 15))

        # ── KPI Cards Row ──
        self.kpi_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.kpi_frame.pack(fill="x", padx=10, pady=(0, 15))
        self.kpi_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        self.kpi_total_tasks = KPICard(self.kpi_frame, title="Total Tasks", value="0", subtitle="all assigned")
        self.kpi_total_tasks.grid(row=0, column=0, padx=4, sticky="ew")

        self.kpi_completion_rate = KPICard(self.kpi_frame, title="Completion Rate", value="0%", subtitle="delivery rate")
        self.kpi_completion_rate.grid(row=0, column=1, padx=4, sticky="ew")

        self.kpi_pending = KPICard(self.kpi_frame, title="In Progress", value="0", subtitle="active tasks")
        self.kpi_pending.grid(row=0, column=2, padx=4, sticky="ew")

        self.kpi_overdue = KPICard(self.kpi_frame, title="Overdue / Delayed", value="0", subtitle="requires attention")
        self.kpi_overdue.grid(row=0, column=3, padx=4, sticky="ew")

        self.kpi_goals = KPICard(self.kpi_frame, title="Strategic Goals", value="0", subtitle="weekly & monthly")
        self.kpi_goals.grid(row=0, column=4, padx=4, sticky="ew")

        self.kpi_team = KPICard(self.kpi_frame, title="Team Size", value="0", subtitle="staff members")
        self.kpi_team.grid(row=0, column=5, padx=4, sticky="ew")

        # ── Modern Charts Row 1 ──
        self.charts_row1 = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.charts_row1.pack(fill="x", padx=10, pady=(0, 12))
        self.charts_row1.grid_columnconfigure((0, 1), weight=1)

        self.chart_status = ChartCard(self.charts_row1, "Task Status Breakdown", fig_width=4.8, fig_height=2.6)
        self.chart_status.grid(row=0, column=0, padx=6, pady=4, sticky="nsew")

        self.chart_priority = ChartCard(self.charts_row1, "Task Priority Distribution", fig_width=4.8, fig_height=2.6)
        self.chart_priority.grid(row=0, column=1, padx=6, pady=4, sticky="nsew")

        # ── Modern Charts Row 2 ──
        self.charts_row2 = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.charts_row2.pack(fill="x", padx=10, pady=(0, 12))
        self.charts_row2.grid_columnconfigure((0, 1), weight=1)

        self.chart_goals = ChartCard(self.charts_row2, "Goals by Timeframe & Status", fig_width=4.8, fig_height=2.6)
        self.chart_goals.grid(row=0, column=0, padx=6, pady=4, sticky="nsew")

        self.chart_compliance = ChartCard(self.charts_row2, "Deadline Health & Compliance", fig_width=4.8, fig_height=2.6)
        self.chart_compliance.grid(row=0, column=1, padx=6, pady=4, sticky="nsew")

        # ── Modern Charts Row 3 ──
        self.charts_row3 = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.charts_row3.pack(fill="x", padx=10, pady=(0, 15))
        self.charts_row3.grid_columnconfigure((0, 1), weight=1)

        self.chart_timeline = ChartCard(self.charts_row3, "Task Creation Trend", fig_width=4.8, fig_height=2.6)
        self.chart_timeline.grid(row=0, column=0, padx=6, pady=4, sticky="nsew")

        self.chart_workload = ChartCard(self.charts_row3, "Workload by Team Member", fig_width=4.8, fig_height=2.6)
        self.chart_workload.grid(row=0, column=1, padx=6, pady=4, sticky="nsew")

        # ── Team Members Overview Badge Frame ──
        self.members_card = ctk.CTkFrame(self.main_area, fg_color=CARD_BG, border_width=1,
                                         border_color=BORDER_COLOR, corner_radius=8)
        self.members_card.pack(fill="x", padx=10, pady=(0, 15))

        lbl_m = ctk.CTkLabel(self.members_card, text="Department Team Roster", font=FONT_BOLD, text_color=TEXT_COLOR)
        lbl_m.pack(anchor="w", padx=16, pady=(12, 6))

        self.members_badges_frame = ctk.CTkFrame(self.members_card, fg_color="transparent")
        self.members_badges_frame.pack(fill="x", padx=16, pady=(0, 12))

        # ── Tasks Table ──
        lbl_tasks = ctk.CTkLabel(self.main_area, text="Department Assigned Tasks", font=FONT_TITLE, text_color=TEXT_COLOR)
        lbl_tasks.pack(anchor="w", padx=10, pady=(5, 5))

        task_cols = [
            {"id": "date", "title": "DATE", "weight": 1.0},
            {"id": "task", "title": "TASK", "weight": 4.5},
            {"id": "person", "title": "OWNER", "weight": 1.5},
            {"id": "priority", "title": "PRIORITY", "weight": 1.0},
            {"id": "status", "title": "STATUS", "weight": 1.2, "type": "pill"},
            {"id": "due_date", "title": "DUE DATE", "weight": 1.2}
        ]
        self.tasks_table = ModernCardTable(self.main_area, columns=task_cols, height=220,
                                           double_click_callback=self._show_task_details)
        self.tasks_table.pack(fill="x", padx=10, pady=(0, 15))

        # ── Goals Table ──
        lbl_goals = ctk.CTkLabel(self.main_area, text="Department Strategic Goals", font=FONT_TITLE, text_color=TEXT_COLOR)
        lbl_goals.pack(anchor="w", padx=10, pady=(5, 5))

        goal_cols = [
            {"id": "timeframe", "title": "TIMEFRAME", "weight": 1.0},
            {"id": "period", "title": "PERIOD", "weight": 1.2},
            {"id": "goal", "title": "GOAL", "weight": 5.0},
            {"id": "person", "title": "OWNER", "weight": 1.5},
            {"id": "status", "title": "STATUS", "weight": 1.2, "type": "pill"}
        ]
        self.goals_table = ModernCardTable(self.main_area, columns=goal_cols, height=180,
                                           double_click_callback=self._show_goal_details)
        self.goals_table.pack(fill="x", padx=10, pady=(0, 20))

    def _select_department(self, name: str):
        self.current_dept_name = name

        for dept_name, btn in self.dept_buttons:
            btn.configure(fg_color=BG_COLOR if dept_name == name else "transparent",
                          font=("Inter", 12, "bold") if dept_name == name else ("Inter", 12))

        all_tasks = self.repository.get_tasks()
        all_goals = self.repository.get_goals()
        all_people = self.repository.get_people()

        tasks = [t for t in all_tasks if getattr(t, 'department', '').strip().lower() == name.lower()]
        goals = [g for g in all_goals if getattr(g, 'department', '').strip().lower() == name.lower()]

        # Identify team members belonging to this department
        team_members = set()
        for p in all_people:
            if getattr(p, 'department', '').strip().lower() == name.lower():
                team_members.add(p.name)
        for t in tasks:
            if getattr(t, 'person', '').strip():
                team_members.add(t.person.strip())
        for g in goals:
            if getattr(g, 'person', '').strip():
                team_members.add(g.person.strip())
        if name in TEAM_STRUCTURE:
            for member in TEAM_STRUCTURE[name]:
                team_members.add(member)

        sorted_members = sorted(team_members)

        # ── Update Header ──
        self.lbl_name.configure(text=f"{name}")
        self.lbl_dept_info.configure(
            text=f"👥 {len(sorted_members)} team members  ·  📋 {len(tasks)} tasks assigned  ·  🎯 {len(goals)} goals tracked"
        )

        # ── Calculate Department Metrics ──
        total_tasks = len(tasks)
        task_status = Counter(t.status.strip().capitalize() for t in tasks)
        completed_tasks = task_status.get("Completed", 0) + task_status.get("Done", 0) + task_status.get("Update", 0)
        pending_tasks = task_status.get("Pending", 0)
        delayed_tasks = task_status.get("Delayed", 0)
        overdue_tasks = sum(1 for t in tasks if _is_overdue(t))
        at_risk_tasks = delayed_tasks + overdue_tasks

        completion_rate = round(completed_tasks / total_tasks * 100) if total_tasks else 0

        # Update KPIs
        self.kpi_total_tasks.set_value(str(total_tasks))
        self.kpi_completion_rate.set_value(f"{completion_rate}%")
        self.kpi_pending.set_value(str(pending_tasks))
        self.kpi_overdue.set_value(str(at_risk_tasks))
        self.kpi_goals.set_value(str(len(goals)))
        self.kpi_team.set_value(str(len(sorted_members)))

        # ── 1. Task Status Chart (Donut) ──
        if tasks:
            merged = defaultdict(int)
            for st, cnt in task_status.items():
                if st.lower() in ("done", "completed", "update"):
                    merged["Completed"] += cnt
                else:
                    merged[st] += cnt
            labels, vals, colors = [], [], []
            for st_name in ["Completed", "Pending", "Delayed"]:
                if st_name in merged:
                    labels.append(st_name)
                    vals.append(merged[st_name])
                    colors.append(STATUS_COLORS[st_name])
            for st_name, cnt in merged.items():
                if st_name not in ["Completed", "Pending", "Delayed"]:
                    labels.append(st_name)
                    vals.append(cnt)
                    colors.append(CHART_COLORS[len(labels) % len(CHART_COLORS)])
            self.chart_status.pie_chart(labels, vals, colors=colors)
        else:
            self.chart_status.clear()
            self.chart_status.ax.text(0.5, 0.5, "No tasks assigned", ha="center", va="center",
                                      fontsize=9, color=TEXT_MUTED, transform=self.chart_status.ax.transAxes)
            self.chart_status.draw()

        # ── 2. Task Priority Chart (Donut) ──
        prio_counts = Counter(t.priority.strip().capitalize() if t.priority.strip() else "Normal" for t in tasks)
        if prio_counts:
            priority_order = ["High", "Normal", "Low"]
            priority_colors = {"High": "#ef4444", "Normal": "#0ea5e9", "Low": "#10b981"}
            p_labels = [p for p in priority_order if p in prio_counts]
            p_labels += [p for p in prio_counts if p not in priority_order]
            p_vals = [prio_counts[l] for l in p_labels]
            p_colors = [priority_colors.get(l, CHART_COLORS[0]) for l in p_labels]
            self.chart_priority.pie_chart(p_labels, p_vals, colors=p_colors)
        else:
            self.chart_priority.clear()
            self.chart_priority.ax.text(0.5, 0.5, "No priority data", ha="center", va="center",
                                        fontsize=9, color=TEXT_MUTED, transform=self.chart_priority.ax.transAxes)
            self.chart_priority.draw()

        # ── 3. Goals Chart (Donut) ──
        tf_counts = Counter(g.timeframe.strip().capitalize() if getattr(g, 'timeframe', '') else "Other" for g in goals)
        if tf_counts:
            tf_labels = list(tf_counts.keys())
            tf_vals = [tf_counts[l] for l in tf_labels]
            tf_colors = ["#6366f1", "#0ea5e9", "#f59e0b", "#10b981"][:len(tf_labels)]
            self.chart_goals.pie_chart(tf_labels, tf_vals, colors=tf_colors)
        else:
            self.chart_goals.clear()
            self.chart_goals.ax.text(0.5, 0.5, "No goals for this department", ha="center", va="center",
                                     fontsize=9, color=TEXT_MUTED, transform=self.chart_goals.ax.transAxes)
            self.chart_goals.draw()

        # ── 4. Deadline Health & Compliance (Donut) ──
        if tasks:
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

            c_labels = ["Completed", "On Track", "Overdue / Delayed", "No Deadline"]
            c_vals = [comp_completed, comp_on_track, comp_overdue, comp_no_dl]
            c_colors = ["#10b981", "#0ea5e9", "#ef4444", "#94a3b8"]
            c_filtered = [(l, v, c) for l, v, c in zip(c_labels, c_vals, c_colors) if v > 0]
            if c_filtered:
                self.chart_compliance.pie_chart([f[0] for f in c_filtered], [f[1] for f in c_filtered], colors=[f[2] for f in c_filtered])
            else:
                self.chart_compliance.clear()
                self.chart_compliance.draw()
        else:
            self.chart_compliance.clear()
            self.chart_compliance.ax.text(0.5, 0.5, "No deadline data", ha="center", va="center",
                                          fontsize=9, color=TEXT_MUTED, transform=self.chart_compliance.ax.transAxes)
            self.chart_compliance.draw()

        # ── 5. Task Creation Trend (Smooth Area Line) ──
        date_counts = defaultdict(int)
        for t in tasks:
            if getattr(t, 'date', '').strip():
                date_counts[t.date.strip()] += 1
        if date_counts:
            sorted_dates = sorted(date_counts.keys())[-12:]
            self.chart_timeline.line_chart(sorted_dates, {"Tasks": [date_counts[d] for d in sorted_dates]})
        else:
            self.chart_timeline.clear()
            self.chart_timeline.ax.text(0.5, 0.5, "No task activity recorded", ha="center", va="center",
                                        fontsize=9, color=TEXT_MUTED, transform=self.chart_timeline.ax.transAxes)
            self.chart_timeline.draw()

        # ── 6. Workload by Team Member (Bar Chart) ──
        member_counts = Counter(t.person.strip() for t in tasks if getattr(t, 'person', '').strip())
        if member_counts:
            sorted_m = sorted(member_counts.items(), key=lambda x: x[1], reverse=True)[:8]
            m_labels = [x[0] for x in sorted_m]
            m_vals = [x[1] for x in sorted_m]
            self.chart_workload.bar_chart(m_labels, m_vals, color=CHART_COLORS[:len(m_labels)])
        else:
            self.chart_workload.clear()
            self.chart_workload.ax.text(0.5, 0.5, "No member workload data", ha="center", va="center",
                                        fontsize=9, color=TEXT_MUTED, transform=self.chart_workload.ax.transAxes)
            self.chart_workload.draw()

        # ── Update Team Members Badges ──
        for w in self.members_badges_frame.winfo_children():
            w.destroy()

        if sorted_members:
            for member in sorted_members:
                m_task_cnt = sum(1 for t in tasks if t.person == member)
                b = ctk.CTkFrame(self.members_badges_frame, fg_color="#f8fafc", corner_radius=6,
                                 border_width=1, border_color=BORDER_COLOR)
                b.pack(side="left", padx=4, pady=4)
                lbl_m_name = ctk.CTkLabel(b, text=f"👤 {member} ({m_task_cnt} tasks)",
                                         font=FONT_SMALL, text_color=TEXT_COLOR)
                lbl_m_name.pack(padx=8, pady=3)
        else:
            ctk.CTkLabel(self.members_badges_frame, text="No members currently registered",
                         font=FONT_SMALL, text_color=TEXT_MUTED).pack(side="left", pady=4)

        # ── Populate Tables ──
        task_data = []
        for t in tasks:
            task_data.append({
                "id": t.id,
                "date": t.date,
                "task": t.task,
                "person": t.person,
                "priority": t.priority,
                "status": t.status,
                "due_date": getattr(t, 'due_date', '') or "—",
                "reason": getattr(t, 'reason', ''),
            })
        self.tasks_table.update_data(task_data)

        goal_data = []
        for g in goals:
            goal_data.append({
                "id": g.id,
                "timeframe": getattr(g, 'timeframe', ''),
                "period": getattr(g, 'period', ''),
                "goal": g.goal,
                "person": getattr(g, 'person', ''),
                "status": g.status,
                "reason": getattr(g, 'reason', ''),
            })
        self.goals_table.update_data(goal_data)

    def refresh_data(self):
        """Called upon data refresh."""
        self.departments = self._get_department_list()
        # Rebuild department buttons
        for w in self.scroll_buttons.winfo_children():
            w.destroy()
        self.dept_buttons = []
        for dept in self.departments:
            btn = ctk.CTkButton(
                self.scroll_buttons,
                text=dept,
                fg_color="transparent",
                text_color=TEXT_COLOR,
                hover_color=BG_COLOR,
                anchor="w",
                font=("Inter", 12),
                height=34,
                command=lambda d=dept: self._select_department(d)
            )
            btn.pack(fill="x", padx=4, pady=2)
            self.dept_buttons.append((dept, btn))

        # Reselect current or first department
        selected = self.current_dept_name if self.current_dept_name in self.departments else (self.departments[0] if self.departments else None)
        if selected:
            self._select_department(selected)

    def _show_task_details(self, row_data):
        top = ctk.CTkToplevel(self)
        top.title("Department Task Details")
        top.geometry("500x480")
        top.attributes("-topmost", True)

        frame = ctk.CTkScrollableFrame(top, fg_color=BG_COLOR)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        display_data = dict(row_data)
        if "id" in display_data:
            del display_data["id"]

        status = display_data.get("status", "")
        reason = display_data.get("reason", "")
        due_date = display_data.get("due_date", "")

        if status.lower() == "delayed" and reason:
            match = re.search(r'\(Old Deadline:\s*(.*?)\)', reason, re.IGNORECASE)
            if match:
                old_deadline = match.group(1)
                actual_reason = reason.replace(match.group(0), "").strip()
                display_data["old_deadline"] = old_deadline
                display_data["new_deadline"] = due_date
                display_data["reason"] = actual_reason
                if "due_date" in display_data:
                    del display_data["due_date"]

        for key, value in display_data.items():
            if not value:
                continue
            if key == "task":
                ctk.CTkLabel(frame, text=f"{key.capitalize()}:", font=("Inter", 12, "bold")).pack(anchor="w", pady=(5, 0))
                txt = ctk.CTkTextbox(frame, height=100)
                txt.pack(fill="x", pady=(0, 10))
                txt.insert("0.0", str(value))
                txt.configure(state="disabled")
            else:
                formatted_key = key.replace("_", " ").title()
                ctk.CTkLabel(frame, text=f"{formatted_key}: {value}", font=("Inter", 12)).pack(anchor="w", pady=2)

    def _show_goal_details(self, row_data):
        top = ctk.CTkToplevel(self)
        top.title("Department Goal Details")
        top.geometry("500x380")
        top.attributes("-topmost", True)

        frame = ctk.CTkScrollableFrame(top, fg_color=BG_COLOR)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        display_data = dict(row_data)
        if "id" in display_data:
            del display_data["id"]

        for key, value in display_data.items():
            if not value:
                continue
            if key == "goal":
                ctk.CTkLabel(frame, text="Goal Statement:", font=("Inter", 12, "bold")).pack(anchor="w", pady=(5, 0))
                txt = ctk.CTkTextbox(frame, height=90)
                txt.pack(fill="x", pady=(0, 10))
                txt.insert("0.0", str(value))
                txt.configure(state="disabled")
            else:
                formatted_key = key.replace("_", " ").title()
                ctk.CTkLabel(frame, text=f"{formatted_key}: {value}", font=("Inter", 12)).pack(anchor="w", pady=2)
