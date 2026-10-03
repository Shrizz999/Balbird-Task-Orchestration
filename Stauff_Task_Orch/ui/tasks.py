import csv
import re
from tkinter import filedialog, messagebox
import customtkinter as ctk
from .components import FilterBar, DataTable, BG_COLOR, TEXT_COLOR, FONT_H1
from data.repository import DataRepository

class TasksView(ctk.CTkFrame):
    def __init__(self, master, repository: DataRepository, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self.repository = repository
        self.all_tasks = self._get_filtered_tasks()
        
        self._build_header()
        self._build_filters()
        self._build_table()
        
    def _get_filtered_tasks(self):
        tasks = self.repository.get_tasks()
        selected_dept = getattr(self.master, "current_dept", "All Departments")
        if hasattr(selected_dept, "get"):
            selected_dept = selected_dept.get()
        if selected_dept != "All Departments":
            return [t for t in tasks if getattr(t, 'department', '') == selected_dept]
        return tasks

        
    def _build_header(self):
        hdr_frame = ctk.CTkFrame(self, fg_color="transparent")
        hdr_frame.pack(fill="x", padx=20, pady=20)
        
        lbl_title = ctk.CTkLabel(hdr_frame, text="All Tasks", font=FONT_H1, text_color=TEXT_COLOR)
        lbl_title.pack(side="left")
        
        btn_export = ctk.CTkButton(hdr_frame, text="Export CSV", command=self._export_csv)
        btn_export.pack(side="right")
        
    def _build_filters(self):
        depts = ["All"] + list(set(t.department for t in self.all_tasks))
        people = ["All"] + list(set(t.person for t in self.all_tasks))
        
        filter_options = [
            {"id": "department", "label": "Department:", "type": "dropdown", "values": depts},
            {"id": "person", "label": "Person:", "type": "dropdown", "values": people},
            {"id": "search", "label": "Search:", "type": "search"}
        ]
        
        self.filter_bar = FilterBar(self, filter_options, self._on_filter_change)
        self.filter_bar.pack(fill="x", padx=20, pady=(0, 20))
        
    def _build_table(self):
        columns = [
            {"id": "date", "title": "Date", "width": 100},
            {"id": "person", "title": "Person", "width": 120},
            {"id": "department", "title": "Department", "width": 150},
            {"id": "task", "title": "Task", "width": 400},
            {"id": "status", "title": "Status", "width": 100}
        ]
        
        self.data_table = DataTable(self, columns=columns, data=self._get_table_data(self.all_tasks), double_click_callback=self._show_details)
        self.data_table.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
    def _get_table_data(self, tasks):
        return [vars(t) for t in tasks]
        
    def _on_filter_change(self, filters):
        # A manual filter change from the UI clears any preset filter
        if hasattr(self, 'preset_filter'):
            self.preset_filter = None
        self._apply_filters(filters)
        
    def apply_preset_filter(self, preset: str):
        # Clear UI filters first (this might trigger _on_filter_change and clear preset)
        if hasattr(self, 'filter_bar'):
            self.filter_bar._clear_filters(trigger=False)
            
        # Set the preset filter AFTER clearing UI
        self.preset_filter = preset
        self._apply_filters()
        
    def _apply_filters(self, filters=None):
        filtered = self.all_tasks
        
        # Apply preset filter if active
        preset = getattr(self, 'preset_filter', None)
        if preset == "Attention Required":
            from .dashboard import _is_overdue
            filtered = [t for t in filtered if t.status.lower() == "delayed" or _is_overdue(t) or (t.priority.strip().lower() in ("high", "critical") and t.status.lower() not in ("completed", "done"))]
        elif preset == "Critical Issues":
            filtered = [t for t in filtered if t.priority.strip().lower() in ("high", "critical") and t.status.strip().lower() not in ("completed", "done")]
        elif preset == "Overdue":
            from .dashboard import _is_overdue
            filtered = [t for t in filtered if _is_overdue(t)]
        elif preset == "At risk":
            filtered = [t for t in filtered if t.status.strip().lower() == "delayed"]
            
        # Apply UI filters
        if filters:
            if filters.get("department") and filters["department"] != "All":
                filtered = [t for t in filtered if t.department == filters["department"]]
                
            if filters.get("person") and filters["person"] != "All":
                filtered = [t for t in filtered if t.person == filters["person"]]
                
            search_term = filters.get("search", "").lower()
            if search_term:
                filtered = [t for t in filtered if search_term in t.task.lower()]
                
        self.data_table.update_data(self._get_table_data(filtered))
        
    def _export_csv(self):
        data = self.data_table.data
        if not data:
            messagebox.showwarning("Export", "No data to export.")
            return
            
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                messagebox.showinfo("Export", f"Successfully exported to {path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}")
                
    def _show_details(self, row_data):
        # Shows a simple popup with full task details
        top = ctk.CTkToplevel(self)
        top.title("Task Details")
        top.geometry("500x500")
        
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

    def refresh_data(self):
        self.all_tasks = self._get_filtered_tasks()
        if hasattr(self, "filter_bar"):
            self.filter_bar.destroy()
            self._build_filters()
            if hasattr(self, "data_table"):
                self.filter_bar.pack(before=self.data_table, fill="x", padx=20, pady=(0, 20))
        self._apply_filters()
