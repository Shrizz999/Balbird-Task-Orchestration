import customtkinter as ctk
from .components import FilterBar, DataTable, BG_COLOR, TEXT_COLOR, FONT_H1
from data.repository import DataRepository

class GoalsView(ctk.CTkFrame):
    def __init__(self, master, repository: DataRepository, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self.repository = repository
        self.all_goals = self._get_filtered_goals()
        
        self._build_header()
        self._build_filters()
        self._build_table()
        
    def _get_filtered_goals(self):
        goals = self.repository.get_goals()
        selected_dept = getattr(self.master, "current_dept", "All Departments")
        if hasattr(selected_dept, "get"):
            selected_dept = selected_dept.get()
        if selected_dept != "All Departments":
            return [g for g in goals if getattr(g, 'department', '') == selected_dept]
        return goals

        
    def _build_header(self):
        hdr_frame = ctk.CTkFrame(self, fg_color="transparent")
        hdr_frame.pack(fill="x", padx=20, pady=20)
        
        lbl_title = ctk.CTkLabel(hdr_frame, text="Goals Management", font=FONT_H1, text_color=TEXT_COLOR)
        lbl_title.pack(side="left")
        
    def _build_filters(self):
        timeframes = ["All"] + list(set(g.timeframe for g in self.all_goals))
        people = ["All"] + list(set(g.person for g in self.all_goals))
        
        filter_options = [
            {"id": "timeframe", "label": "Time Frame:", "type": "dropdown", "values": timeframes},
            {"id": "person", "label": "Person:", "type": "dropdown", "values": people},
            {"id": "search", "label": "Search:", "type": "search"}
        ]
        
        self.filter_bar = FilterBar(self, filter_options, self._on_filter_change)
        self.filter_bar.pack(fill="x", padx=20, pady=(0, 20))
        
    def _build_table(self):
        columns = [
            {"id": "timeframe", "title": "Time Frame", "width": 100},
            {"id": "period", "title": "Period", "width": 120},
            {"id": "person", "title": "Person", "width": 120},
            {"id": "department", "title": "Department", "width": 150},
            {"id": "goal", "title": "Goal", "width": 500}
        ]
        
        self.data_table = DataTable(self, columns=columns, data=self._get_table_data(self.all_goals))
        self.data_table.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
    def _get_table_data(self, goals):
        return [vars(g) for g in goals]
        
    def _on_filter_change(self, filters):
        filtered = self.all_goals
        
        if filters.get("timeframe") and filters["timeframe"] != "All":
            filtered = [g for g in filtered if g.timeframe == filters["timeframe"]]
            
        if filters.get("person") and filters["person"] != "All":
            filtered = [g for g in filtered if g.person == filters["person"]]
            
        search_term = filters.get("search", "").lower()
        if search_term:
            filtered = [g for g in filtered if search_term in g.goal.lower()]
            
        self.data_table.update_data(self._get_table_data(filtered))

    def refresh_data(self):
        self.all_goals = self._get_filtered_goals()
        if hasattr(self, "filter_bar"):
            self.filter_bar.destroy()
            self._build_filters()
            if hasattr(self, "data_table"):
                self.filter_bar.pack(before=self.data_table, fill="x", padx=20, pady=(0, 20))
        self.data_table.update_data(self._get_table_data(self.all_goals))
