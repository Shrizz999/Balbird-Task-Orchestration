import customtkinter as ctk
from collections import Counter, defaultdict
from .components import (KPICard, ChartCard, BG_COLOR, TEXT_COLOR,
                         FONT_H1, FONT_TITLE, CARD_BG, BORDER_COLOR,
                         CHART_COLORS, TEXT_MUTED)
from data.repository import DataRepository


class AnalyticsView(ctk.CTkFrame):
    def __init__(self, master, repository: DataRepository, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self.repository = repository

        lbl_title = ctk.CTkLabel(self, text="Department & People Analytics", font=FONT_H1, text_color=TEXT_COLOR)
        lbl_title.pack(anchor="w", padx=20, pady=(20, 5))

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self._last_data_sig = None
        self.build_content(force=True)

    def build_content(self, force: bool = False):
        people = self.repository.get_people()
        tasks = self.repository.get_tasks()
        goals = self.repository.get_goals()
        updates = self.repository.get_updates()

        selected_dept = getattr(self.master, "current_dept", "All Departments")
        if hasattr(selected_dept, "get"):
            selected_dept = selected_dept.get()

        data_sig = (
            selected_dept,
            len(people),
            tuple((p.name, getattr(p, 'department', '')) for p in people),
            len(tasks),
            tuple((t.id, getattr(t, 'department', '')) for t in tasks),
            len(goals),
            len(updates)
        )

        if not force and self._last_data_sig == data_sig:
            return

        scroll_y = 0.0
        try:
            scroll_y = self.scroll_frame._parent_canvas.yview()[0]
        except Exception:
            pass

        self._last_data_sig = data_sig

        for w in self.scroll_frame.winfo_children():
            w.destroy()
            
        if selected_dept != "All Departments":
            people = [p for p in people if getattr(p, 'department', '') == selected_dept]
            tasks = [t for t in tasks if getattr(t, 'department', '') == selected_dept]
            goals = [g for g in goals if getattr(g, 'department', '') == selected_dept]
            updates = [u for u in updates if getattr(u, 'department', '') == selected_dept]

        departments = sorted(set(p.department for p in people))

        # --- Top Level Charts ---
        top_charts = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        top_charts.pack(fill="x", pady=(0, 20))
        top_charts.grid_columnconfigure((0, 1, 2), weight=1)

        # Tasks by department
        chart1 = ChartCard(top_charts, "Tasks by Department", fig_width=4, fig_height=2.5)
        chart1.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        dept_task_counts = Counter(t.department for t in tasks)
        if dept_task_counts:
            chart1.bar_chart(list(dept_task_counts.keys()), list(dept_task_counts.values()),
                             color=CHART_COLORS[:len(dept_task_counts)])

        # Goals by department
        chart2 = ChartCard(top_charts, "Goals by Department", fig_width=4, fig_height=2.5)
        chart2.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        dept_goal_counts = Counter(g.department for g in goals)
        if dept_goal_counts:
            chart2.pie_chart(list(dept_goal_counts.keys()), list(dept_goal_counts.values()))

        # Updates by department
        chart3 = ChartCard(top_charts, "Updates by Department", fig_width=4, fig_height=2.5)
        chart3.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        dept_update_counts = Counter(u.department for u in updates if u.person.lower() != "boss")
        if dept_update_counts:
            chart3.bar_chart(list(dept_update_counts.keys()), list(dept_update_counts.values()),
                             color=CHART_COLORS[:len(dept_update_counts)])

        # --- Per-Person Comparison ---
        comparison_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        comparison_frame.pack(fill="x", pady=(0, 20))
        comparison_frame.grid_columnconfigure((0, 1), weight=1)

        # Person comparison: tasks vs goals vs updates
        chart4 = ChartCard(comparison_frame, "Person Workload Comparison", fig_width=5, fig_height=3)
        chart4.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        person_names = sorted(set(p.name for p in people))
        if person_names:
            task_vals = [sum(1 for t in tasks if t.person == n) for n in person_names]
            goal_vals = [sum(1 for g in goals if g.person == n) for n in person_names]
            update_vals = [sum(1 for u in updates if u.person == n) for n in person_names]

            chart4.clear()
            import numpy as np
            x = np.arange(len(person_names))
            w = 0.25
            chart4.ax.bar(x - w, task_vals, w, label='Tasks', color=CHART_COLORS[0])
            chart4.ax.bar(x, goal_vals, w, label='Goals', color=CHART_COLORS[1])
            chart4.ax.bar(x + w, update_vals, w, label='Updates', color=CHART_COLORS[2])
            chart4.ax.set_xticks(x)
            chart4.ax.set_xticklabels(person_names, fontsize=8)
            chart4.ax.legend(fontsize=7, frameon=False, labelcolor=TEXT_MUTED)
            chart4.draw()

        # Activity timeline per person
        chart5 = ChartCard(comparison_frame, "Task Timeline by Person", fig_width=5, fig_height=3)
        chart5.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        all_dates = sorted(set(t.date for t in tasks))
        if all_dates and person_names:
            datasets = {}
            for name in person_names:
                person_date_counts = Counter(t.date for t in tasks if t.person == name)
                datasets[name] = [person_date_counts.get(d, 0) for d in all_dates]
            chart5.line_chart(all_dates, datasets)

        # --- Per Department Detail ---
        for dept in departments:
            dept_frame = ctk.CTkFrame(self.scroll_frame, fg_color=CARD_BG,
                                      border_width=1, border_color=BORDER_COLOR, corner_radius=8)
            dept_frame.pack(fill="x", pady=(0, 15))

            lbl_dept = ctk.CTkLabel(dept_frame, text=dept, font=FONT_TITLE, text_color=TEXT_COLOR)
            lbl_dept.pack(anchor="w", padx=20, pady=(15, 8))

            dept_people = [p for p in people if p.department == dept]
            dept_tasks = [t for t in tasks if t.department == dept]
            dept_goals = [g for g in goals if g.department == dept]
            dept_updates = [u for u in updates if u.department == dept]

            kpi_frame = ctk.CTkFrame(dept_frame, fg_color="transparent")
            kpi_frame.pack(fill="x", padx=15, pady=(0, 15))
            kpi_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

            KPICard(kpi_frame, "Team Size", str(len(dept_people))).grid(row=0, column=0, padx=5, sticky="ew")
            KPICard(kpi_frame, "Tasks", str(len(dept_tasks))).grid(row=0, column=1, padx=5, sticky="ew")
            KPICard(kpi_frame, "Goals", str(len(dept_goals))).grid(row=0, column=2, padx=5, sticky="ew")
            KPICard(kpi_frame, "Updates", str(len(dept_updates))).grid(row=0, column=3, padx=5, sticky="ew")

            members_text = ", ".join(p.name for p in dept_people)
            lbl_members = ctk.CTkLabel(dept_frame, text=f"Members: {members_text}", font=("Inter", 11), text_color=TEXT_MUTED)
            lbl_members.pack(anchor="w", padx=20, pady=(0, 15))

        def _restore():
            try:
                self.scroll_frame._parent_canvas.yview_moveto(scroll_y)
            except Exception:
                pass
        self.after_idle(_restore)
        self.after(50, _restore)

    def refresh_data(self):
        self.build_content(force=False)
