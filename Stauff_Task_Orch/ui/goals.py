import customtkinter as ctk
from .components import FilterBar, ModernCardTable, BG_COLOR, TEXT_COLOR, FONT_H1
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
            return [g for g in goals if getattr(g, 'department', '').lower() == selected_dept.lower()]
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
            {"id": "id", "title": "GOAL ID", "weight": 1.0},
            {"id": "timeframe", "title": "TIMEFRAME", "weight": 1.0, "type": "pill"},
            {"id": "period", "title": "PERIOD", "weight": 1.0},
            {"id": "department", "title": "DEPARTMENT", "weight": 1.2},
            {"id": "person", "title": "EMPLOYEE", "weight": 1.2},
            {"id": "goal", "title": "GOAL", "weight": 2.0},
            {"id": "status", "title": "STATUS", "weight": 1.0, "type": "pill"}
        ]
        
        self.data_table = ModernCardTable(self, columns=columns, data=self._get_table_data(self.all_goals), double_click_callback=self._show_details)
        self.data_table.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
    def _get_table_data(self, goals):
        data = []
        for g in goals:
            row = vars(g).copy()
            if row.get("id"):
                row["id"] = str(row["id"])[-4:]
            checklist = getattr(g, 'checklist', None)
            if checklist:
                comp = 0
                for item in checklist:
                    if isinstance(item, dict) and item.get("completed"):
                        comp += 1
                    elif isinstance(item, str) and item.startswith("[x]"):
                        comp += 1
                row["progress"] = (comp / len(checklist)) * 100
            data.append(row)
        return data
        
    def _show_details(self, row_data):
        top = ctk.CTkToplevel(self)
        top.title("Goal Details")
        top.geometry("500x500")
        
        frame = ctk.CTkScrollableFrame(top, fg_color=BG_COLOR)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        display_data = dict(row_data)
        if "id" in display_data:
            del display_data["id"]
                    
        for key, value in display_data.items():
            if not value:
                continue
                
            if key == "goal":
                lbl = ctk.CTkLabel(frame, text=f"{key.capitalize()}:", font=("Inter", 12, "bold"))
                lbl.pack(anchor="w", pady=(5, 0))
                txt = ctk.CTkTextbox(frame, height=100)
                txt.pack(fill="x", pady=(0, 10))
                txt.insert("0.0", str(value))
                txt.configure(state="disabled")
            elif key == "checklist" and isinstance(value, list):
                lbl = ctk.CTkLabel(frame, text="Checklist:", font=("Inter", 12, "bold"))
                lbl.pack(anchor="w", pady=(5, 0))
                for item in value:
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
                    chk = ctk.CTkCheckBox(frame, text=text, state="disabled")
                    if is_checked: chk.select()
                    chk.pack(anchor="w", pady=2)
            else:
                formatted_key = key.replace("_", " ").title()
                lbl = ctk.CTkLabel(frame, text=f"{formatted_key}: {value}", font=("Inter", 12))
                lbl.pack(anchor="w", pady=2)
        
    def _on_filter_change(self, filters):
        filtered = self.all_goals
        
        if filters.get("timeframe") and filters["timeframe"] != "All":
            filtered = [g for g in filtered if getattr(g, 'timeframe', '').lower() == filters["timeframe"].lower()]
            
        if filters.get("person") and filters["person"] != "All":
            filtered = [g for g in filtered if getattr(g, 'person', '').lower() == filters["person"].lower()]
            
        search_term = filters.get("search", "").lower()
        if search_term:
            filtered = [g for g in filtered if search_term in getattr(g, 'goal', '').lower() or search_term in getattr(g, 'id', '').lower()]
            
        self.data_table.update_data(self._get_table_data(filtered))

    def refresh_data(self):
        self.all_goals = self._get_filtered_goals()
        
        current_filters = {}
        if hasattr(self, "filter_bar"):
            current_filters = {k: v.get() for k, v in self.filter_bar.filter_vars.items()}
            self.filter_bar.destroy()
            self._build_filters()
            
            for k, v in current_filters.items():
                if k in self.filter_bar.filter_vars:
                    opt = next((o for o in self.filter_bar.filter_options if o["id"] == k), None)
                    if opt and opt["type"] == "search":
                        self.filter_bar.filter_vars[k].set(v)
                    elif opt and v in opt.get("values", []):
                        self.filter_bar.filter_vars[k].set(v)
                        
            if hasattr(self, "data_table"):
                self.data_table.pack_forget()
                self.filter_bar.pack(fill="x", padx=20, pady=(0, 20))
                self.data_table.pack(fill="both", expand=True, padx=20, pady=(0, 20))
                
        filters = {k: v.get() for k, v in self.filter_bar.filter_vars.items()} if hasattr(self, "filter_bar") else {}
        self._on_filter_change(filters)
