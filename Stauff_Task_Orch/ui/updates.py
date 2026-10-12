import customtkinter as ctk
from .components import FilterBar, ModernCardTable, BG_COLOR, TEXT_COLOR, FONT_H1
from data.repository import DataRepository

class UpdatesView(ctk.CTkFrame):
    def __init__(self, master, repository: DataRepository, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self.repository = repository
        self.all_updates = self._get_filtered_updates()
        
        self._build_header()
        self._build_filters()
        self._build_table()
        
    def _get_filtered_updates(self):
        updates = self.repository.get_updates()
        selected_dept = getattr(self.master, "current_dept", "All Departments")
        if hasattr(selected_dept, "get"):
            selected_dept = selected_dept.get()
        if selected_dept != "All Departments":
            return [u for u in updates if getattr(u, 'department', '') == selected_dept]
        return updates

        
    def _build_header(self):
        hdr_frame = ctk.CTkFrame(self, fg_color="transparent")
        hdr_frame.pack(fill="x", padx=20, pady=20)
        
        lbl_title = ctk.CTkLabel(hdr_frame, text="Daily Updates", font=FONT_H1, text_color=TEXT_COLOR)
        lbl_title.pack(side="left")
        
    def _build_filters(self):
        people = ["All"] + list(set(u.person for u in self.all_updates))
        depts = ["All"] + list(set(u.department for u in self.all_updates))
        
        filter_options = [
            {"id": "person", "label": "Person:", "type": "dropdown", "values": people},
            {"id": "department", "label": "Department:", "type": "dropdown", "values": depts},
            {"id": "search", "label": "Search:", "type": "search"}
        ]
        
        self.filter_bar = FilterBar(self, filter_options, self._on_filter_change)
        self.filter_bar.pack(fill="x", padx=20, pady=(0, 20))
        
    def _build_table(self):
        columns = [
            {"id": "date", "title": "DATE", "weight": 1.0},
            {"id": "person", "title": "PERSON", "weight": 1.2},
            {"id": "department", "title": "DEPARTMENT", "weight": 1.5},
            {"id": "report", "title": "REPORT", "weight": 5.0},
            {"id": "rating", "title": "RATING", "weight": 1.0, "type": "pill"}
        ]
        
        self.data_table = ModernCardTable(self, columns=columns, data=self._get_table_data(self.all_updates), double_click_callback=self._show_details)
        self.data_table.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
    def _get_table_data(self, updates):
        data = []
        for u in updates:
            u_dict = vars(u).copy()
            u_dict["rating"] = u_dict.get("rating") or "N/A"
            data.append(u_dict)
        return data
        
    def _on_filter_change(self, filters):
        filtered = self.all_updates
        
        if filters.get("person") and filters["person"] != "All":
            filtered = [u for u in filtered if u.person == filters["person"]]
            
        if filters.get("department") and filters["department"] != "All":
            filtered = [u for u in filtered if u.department == filters["department"]]
            
        search_term = filters.get("search", "").lower()
        if search_term:
            filtered = [u for u in filtered if search_term in u.report.lower()]
            
        self.data_table.update_data(self._get_table_data(filtered))
        
    def _show_details(self, row_data):
        top = ctk.CTkToplevel(self)
        top.title("Update Details")
        top.geometry("500x300")
        
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

    def refresh_data(self):
        self.all_updates = self._get_filtered_updates()
        if hasattr(self, "filter_bar"):
            self.filter_bar.destroy()
            self._build_filters()
            if hasattr(self, "data_table"):
                self.data_table.pack_forget()
                self.filter_bar.pack(fill="x", padx=20, pady=(0, 20))
                self.data_table.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.data_table.update_data(self._get_table_data(self.all_updates))
