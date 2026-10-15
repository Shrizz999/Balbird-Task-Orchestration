import customtkinter as ctk
from collections import Counter, defaultdict
from .components import (KPICard, ChartCard, ModernCardTable, BG_COLOR, TEXT_COLOR,
                         FONT_H1, FONT_TITLE, CARD_BG, BORDER_COLOR, TEXT_MUTED,
                         CHART_COLORS)
from data.repository import DataRepository
import config


class PeopleView(ctk.CTkFrame):
    def __init__(self, master, repository: DataRepository, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self.repository = repository
        self.people = self._get_filtered_people()
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_main_area()

        if self.people:
            self._select_person(self.people[0].name)

    def _get_filtered_people(self):
        people = self.repository.get_people()
        selected_dept = getattr(self.master, "current_dept", "All Departments")
        if hasattr(selected_dept, "get"):
            selected_dept = selected_dept.get()
        if selected_dept != "All Departments":
            return [p for p in people if getattr(p, 'department', '') == selected_dept]
        return people

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=CARD_BG, border_width=1,
                                    border_color=BORDER_COLOR, corner_radius=0, width=200)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        lbl_title = ctk.CTkLabel(self.sidebar, text="Team Members", font=FONT_TITLE, text_color=TEXT_COLOR)
        lbl_title.pack(pady=20, padx=10)

        self.person_buttons = []
        for person in self.people:
            btn = ctk.CTkButton(self.sidebar, text=f"{person.name}", fg_color="transparent",
                                text_color=TEXT_COLOR, hover_color=BG_COLOR, anchor="w",
                                command=lambda p=person.name: self._select_person(p))
            btn.pack(fill="x", padx=10, pady=3)
            self.person_buttons.append((person.name, btn))

    def _build_main_area(self):
        self.main_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", pady=10, padx=(0, 10))

        # Header
        self.lbl_name = ctk.CTkLabel(self.main_area, text="", font=FONT_H1, text_color=TEXT_COLOR)
        self.lbl_name.pack(anchor="w", padx=10, pady=(0, 2))

        self.lbl_dept = ctk.CTkLabel(self.main_area, text="", font=("Inter", 13), text_color=TEXT_MUTED)
        self.lbl_dept.pack(anchor="w", padx=10, pady=(0, 15))

        # KPIs
        self.kpi_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.kpi_frame.pack(fill="x", padx=10, pady=(0, 15))
        show_updates = getattr(config, "SHOW_DAILY_UPDATES", False)
        cols = 5 if show_updates else 4
        self.kpi_frame.grid_columnconfigure(tuple(range(cols)), weight=1)

        self.kpi_tasks = KPICard(self.kpi_frame, title="Total Tasks", value="0")
        self.kpi_tasks.grid(row=0, column=0, padx=5, sticky="ew")
        self.kpi_goals = KPICard(self.kpi_frame, title="Goals", value="0")
        self.kpi_goals.grid(row=0, column=1, padx=5, sticky="ew")
        col_idx = 2
        if show_updates:
            self.kpi_updates = KPICard(self.kpi_frame, title="Updates", value="0")
            self.kpi_updates.grid(row=0, column=col_idx, padx=5, sticky="ew")
            col_idx += 1
        self.kpi_weekly = KPICard(self.kpi_frame, title="Weekly Goals", value="0")
        self.kpi_weekly.grid(row=0, column=col_idx, padx=5, sticky="ew")
        col_idx += 1
        self.kpi_sos = KPICard(self.kpi_frame, title="SOs Pushed", value="0")
        self.kpi_sos.grid(row=0, column=col_idx, padx=5, sticky="ew")

        # Charts row
        self.charts_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.charts_frame.pack(fill="x", padx=10, pady=(0, 15))
        self.charts_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.chart_timeline = ChartCard(self.charts_frame, "Task Activity", fig_width=3.5, fig_height=2.2)
        self.chart_timeline.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.chart_goals = ChartCard(self.charts_frame, "Goals Breakdown", fig_width=3.5, fig_height=2.2)
        self.chart_goals.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.chart_status = ChartCard(self.charts_frame, "Task Status", fig_width=3.5, fig_height=2.2)
        self.chart_status.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

        # Tasks table
        lbl_tasks = ctk.CTkLabel(self.main_area, text="Assigned Tasks", font=FONT_TITLE, text_color=TEXT_COLOR)
        lbl_tasks.pack(anchor="w", padx=10, pady=(5, 5))

        task_cols = [
            {"id": "date", "title": "DATE", "weight": 1.0},
            {"id": "task", "title": "TASK", "weight": 5.0},
            {"id": "status", "title": "STATUS", "weight": 1.0, "type": "pill"}
        ]
        self.tasks_table = ModernCardTable(self.main_area, columns=task_cols, height=180, double_click_callback=self._show_task_details)
        self.tasks_table.pack(fill="x", padx=10, pady=(0, 15))

        if show_updates:
            # Updates table
            self.lbl_updates = ctk.CTkLabel(self.main_area, text="Historical Updates (AI Reports)", font=FONT_TITLE, text_color=TEXT_COLOR)
            self.lbl_updates.pack(anchor="w", padx=10, pady=(5, 5))

            update_cols = [
                {"id": "date", "title": "DATE", "weight": 1.0},
                {"id": "report", "title": "REPORT", "weight": 6.0}
            ]
            self.updates_table = ModernCardTable(self.main_area, columns=update_cols, height=180, double_click_callback=self._show_update_details)
            self.updates_table.pack(fill="x", padx=10, pady=(0, 15))



        # Sales Orders table
        lbl_sos = ctk.CTkLabel(self.main_area, text="Sales Orders Pushed", font=FONT_TITLE, text_color=TEXT_COLOR)
        lbl_sos.pack(anchor="w", padx=10, pady=(5, 5))

        so_cols = [
            {"id": "po_number", "title": "SO NUMBER", "weight": 1.5},
            {"id": "time", "title": "TIME", "weight": 1.0},
            {"id": "company_name", "title": "COMPANY NAME", "weight": 2.0},
            {"id": "filename", "title": "DOCUMENT", "weight": 2.0}
        ]
        self.so_table = ModernCardTable(self.main_area, columns=so_cols, height=180, double_click_callback=self._open_so_file)
        self.so_table.pack(fill="x", padx=10, pady=(0, 20))

    def _open_so_file(self, row_data):
        po_num = row_data.get("po_number")
        for so in self.repository.get_sales_orders():
            if so.po_number == po_num:
                popup = ctk.CTkToplevel(self)
                popup.title(f"Sales Order Details - {so.po_number}")
                popup.geometry("500x400")
                popup.attributes("-topmost", True)
                
                header = ctk.CTkLabel(popup, text=f"Order: {so.po_number}\nCompany: {so.company_name}", font=("Inter", 16, "bold"))
                header.pack(pady=10)
                
                if so.filename:
                    lbl_file = ctk.CTkLabel(popup, text=f"Document: {so.filename}", font=("Inter", 12))
                    lbl_file.pack(pady=5)
                
                txt_items = ctk.CTkTextbox(popup, width=450, height=250)
                txt_items.pack(pady=10, padx=20)
                txt_items.insert("1.0", so.items_data if so.items_data else "No items found in this order.")
                txt_items.configure(state="disabled")
                
                btn_close = ctk.CTkButton(popup, text="Close", command=popup.destroy)
                btn_close.pack(pady=10)
                break

    def _show_task_details(self, row_data):
        import re
        top = ctk.CTkToplevel(self)
        top.title("Task Details")
        top.geometry("500x500")
        top.attributes("-topmost", True)
        
        frame = ctk.CTkScrollableFrame(top, fg_color=BG_COLOR)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
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
                lbl = ctk.CTkLabel(frame, text=f"{key.capitalize()}:", font=("Inter", 12, "bold"))
                lbl.pack(anchor="w", pady=(5, 0))
                txt = ctk.CTkTextbox(frame, height=100)
                txt.pack(fill="x", pady=(0, 10))
                txt.insert("0.0", str(value))
                txt.configure(state="disabled")
            else:
                formatted_key = key.replace("_", " ").title()
                lbl = ctk.CTkLabel(frame, text=f"{formatted_key}: {value}", font=("Inter", 12))
                lbl.pack(anchor="w", pady=2)

    def _show_update_details(self, row_data):
        top = ctk.CTkToplevel(self)
        top.title("Update Details")
        top.geometry("500x300")
        top.attributes("-topmost", True)
        
        frame = ctk.CTkScrollableFrame(top, fg_color=BG_COLOR)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        display_data = dict(row_data)
        if "id" in display_data:
            del display_data["id"]
            
        for key, value in display_data.items():
            if not value:
                continue
                
            if key == "report":
                lbl = ctk.CTkLabel(frame, text=f"{key.capitalize()}:", font=("Inter", 12, "bold"))
                lbl.pack(anchor="w", pady=(5, 0))
                txt = ctk.CTkTextbox(frame, height=100)
                txt.pack(fill="x", pady=(0, 10))
                txt.insert("0.0", str(value))
                txt.configure(state="disabled")
            else:
                formatted_key = key.replace("_", " ").title()
                lbl = ctk.CTkLabel(frame, text=f"{formatted_key}: {value}", font=("Inter", 12))
                lbl.pack(anchor="w", pady=2)

    def _select_person(self, name: str):
        self.current_selected_person = name
        scroll_y = 0.0
        try:
            scroll_y = self.main_area._parent_canvas.yview()[0]
        except Exception:
            pass

        for p_name, btn in self.person_buttons:
            btn.configure(fg_color=BG_COLOR if p_name == name else "transparent")

        person = next((p for p in self.people if p.name == name), None)
        if not person:
            return

        tasks = [t for t in self.repository.get_tasks() if t.person == name]
        goals = [g for g in self.repository.get_goals() if g.person == name]
        updates = [u for u in self.repository.get_updates() if u.person == name]
        sales_orders = [so for so in self.repository.get_sales_orders() if so.person == name]
        weekly_goals = [g for g in goals if g.timeframe == "Weekly"]

        self.lbl_name.configure(text=person.name)
        self.lbl_dept.configure(text=f"{person.department}")

        self.kpi_tasks.set_value(str(len(tasks)))
        self.kpi_goals.set_value(str(len(goals)))
        if hasattr(self, 'kpi_updates'):
            self.kpi_updates.set_value(str(len(updates)))
        self.kpi_weekly.set_value(str(len(weekly_goals)))
        self.kpi_sos.set_value(str(len(sales_orders)))

        # Task activity timeline
        date_counts = Counter(t.date for t in tasks)
        if date_counts:
            sorted_dates = sorted(date_counts.keys())
            self.chart_timeline.line_chart(sorted_dates, {name: [date_counts[d] for d in sorted_dates]})
        else:
            self.chart_timeline.clear()
            self.chart_timeline.ax.text(0.5, 0.5, "No data", ha="center", va="center",
                                        fontsize=10, color=TEXT_MUTED, transform=self.chart_timeline.ax.transAxes)
            self.chart_timeline.draw()

        # Goals breakdown
        tf_counts = Counter(g.timeframe for g in goals)
        if tf_counts:
            self.chart_goals.pie_chart(list(tf_counts.keys()), list(tf_counts.values()))
        else:
            self.chart_goals.clear()
            self.chart_goals.ax.text(0.5, 0.5, "No data", ha="center", va="center",
                                     fontsize=10, color=TEXT_MUTED, transform=self.chart_goals.ax.transAxes)
            self.chart_goals.draw()

        # Task Status breakdown
        status_counts = Counter(t.status for t in tasks)
        if status_counts:
            labels, values, colors = [], [], []
            for k, v in status_counts.items():
                labels.append(k)
                values.append(v)
                kl = k.lower()
                if "completed" in kl or "done" in kl: colors.append("#10b981")
                elif "delayed" in kl or "overdue" in kl: colors.append("#ef4444")
                else: colors.append("#f59e0b")
            self.chart_status.pie_chart(labels, values, colors)
        else:
            self.chart_status.clear()
            self.chart_status.ax.text(0.5, 0.5, "No data", ha="center", va="center",
                                      fontsize=10, color=TEXT_MUTED, transform=self.chart_status.ax.transAxes)
            self.chart_status.draw()

        self.tasks_table.update_data([vars(t) for t in tasks])
        if hasattr(self, 'updates_table'):
            self.updates_table.update_data([vars(u) for u in updates])

        self.so_table.update_data([vars(so) for so in sales_orders])

        def _restore():
            try:
                self.main_area._parent_canvas.yview_moveto(scroll_y)
            except Exception:
                pass
        self.after_idle(_restore)
        self.after(50, _restore)

    def refresh_data(self):
        new_people = self._get_filtered_people()
        new_names = [p.name for p in new_people]
        cur_names = [name for name, _ in getattr(self, "person_buttons", [])]

        if new_names != cur_names:
            self.people = new_people
            for _, btn in getattr(self, "person_buttons", []):
                btn.destroy()
            self.person_buttons = []
            for person in self.people:
                btn = ctk.CTkButton(self.sidebar, text=f"{person.name}", fg_color="transparent",
                                    text_color=TEXT_COLOR, hover_color=BG_COLOR, anchor="w",
                                    command=lambda p=person.name: self._select_person(p))
                btn.pack(fill="x", padx=10, pady=3)
                self.person_buttons.append((person.name, btn))
        else:
            self.people = new_people

        selected = getattr(self, "current_selected_person", None)
        if selected and any(p.name == selected for p in self.people):
            self._select_person(selected)
        elif self.people:
            self._select_person(self.people[0].name)
        else:
            self._clear_person_view()

    def _clear_person_view(self):
        self.lbl_name.configure(text="No team members")
        self.lbl_dept.configure(text="")
        self.kpi_tasks.set_value("0")
        self.kpi_goals.set_value("0")
        if hasattr(self, 'kpi_updates'):
            self.kpi_updates.set_value("0")
        self.kpi_weekly.set_value("0")
        self.kpi_sos.set_value("0")
        self.chart_timeline.clear()
        self.chart_timeline.draw()
        self.chart_goals.clear()
        self.chart_goals.draw()
        self.chart_status.clear()
        self.chart_status.draw()
        self.tasks_table.update_data([])
        if hasattr(self, 'updates_table'):
            self.updates_table.update_data([])
        self.so_table.update_data([])
