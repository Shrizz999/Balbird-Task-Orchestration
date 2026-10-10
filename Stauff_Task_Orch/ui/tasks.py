import csv
import re
from tkinter import filedialog, messagebox
import customtkinter as ctk
from .components import FilterBar, ModernCardTable, BG_COLOR, TEXT_COLOR, FONT_H1
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
            return [t for t in tasks if getattr(t, 'department', '').lower() == selected_dept.lower()]
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
            {"id": "id", "title": "TASK ID", "weight": 1.2},
            {"id": "task", "title": "TASK", "weight": 1.8},
            {"id": "person", "title": "EMPLOYEE", "weight": 1.2},
            {"id": "priority", "title": "PRIORITY", "weight": 1.0, "type": "pill"},
            {"id": "status", "title": "STATUS", "weight": 1.0, "type": "pill"},
            {"id": "progress", "title": "PROGRESS", "weight": 1.5, "type": "progress"},
            {"id": "date", "title": "ASSIGNED DATE", "weight": 1.0},
            {"id": "due_date", "title": "DEADLINE", "weight": 1.0},
            {"id": "days_overdue", "title": "DAYS OVERDUE", "weight": 1.0},
            {"id": "action", "title": "ACTION", "weight": 0.5, "type": "action"}
        ]
        
        self.data_table = ModernCardTable(self, columns=columns, data=self._get_table_data(self.all_tasks), double_click_callback=self._show_details)
        self.data_table.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
    def _get_table_data(self, tasks):
        from datetime import datetime
        data = []
        for t in tasks:
            row = vars(t).copy()
            if row.get("id"):
                row["id"] = str(row["id"])[-4:]
            checklist = getattr(t, 'checklist', None)
            if not checklist:
                prog = 100.0 if t.status.lower() in ("completed", "done", "update") else 0.0
            else:
                comp = 0
                for item in checklist:
                    if isinstance(item, dict) and item.get("completed"):
                        comp += 1
                    elif isinstance(item, str) and item.startswith("[x]"):
                        comp += 1
                prog = (comp / len(checklist)) * 100
            row["progress"] = prog
            row["due_date"] = row.get("due_date", "") or "-"
            
            days_overdue = 0
            if t.status.lower() not in ("completed", "done", "update") and row["due_date"] != "-":
                for fmt in ("%d/%m/%Y", "%d/%m", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
                    try:
                        dt = datetime.strptime(row["due_date"].strip(), fmt)
                        delta = (datetime.now().date() - dt.date()).days
                        if delta > 0:
                            days_overdue = delta
                        break
                    except (ValueError, AttributeError):
                        pass
            row["days_overdue"] = days_overdue if days_overdue > 0 else "-"
            
            if days_overdue > 0 and str(row.get("status", "")).lower() not in ("completed", "done", "update"):
                row["status"] = "Delayed"
            
            data.append(row)
        return data
        
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
        if filters is None and hasattr(self, 'filter_bar'):
            filters = {k: v.get() for k, v in self.filter_bar.filter_vars.items()}
            
        filtered = self.all_tasks
        
        # Apply preset filter if active
        preset = getattr(self, 'preset_filter', None)
        if preset == "Attention Required":
            from .dashboard import _is_overdue
            filtered = [t for t in filtered if t.status.lower() == "delayed" or _is_overdue(t) or (t.priority.strip().lower() in ("high", "critical") and t.status.lower() not in ("completed", "done", "update"))]
        elif preset == "Critical Issues":
            filtered = [t for t in filtered if t.priority.strip().lower() in ("high", "critical") and t.status.strip().lower() not in ("completed", "done", "update")]
        elif preset == "Overdue":
            from .dashboard import _is_overdue
            filtered = [t for t in filtered if _is_overdue(t)]
        elif preset == "At risk":
            filtered = [t for t in filtered if t.status.strip().lower() == "delayed"]
            
        # Apply UI filters
        if filters:
            if filters.get("department") and filters["department"] != "All":
                filtered = [t for t in filtered if getattr(t, 'department', '').lower() == filters["department"].lower()]
                
            if filters.get("person") and filters["person"] != "All":
                filtered = [t for t in filtered if getattr(t, 'person', '').lower() == filters["person"].lower()]
                
            search_term = filters.get("search", "").lower()
            if search_term:
                filtered = [t for t in filtered if search_term in getattr(t, 'task', '').lower() or search_term in getattr(t, 'id', '').lower()]
                
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

    def refresh_data(self):
        self.all_tasks = self._get_filtered_tasks()
        
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
                
        self._apply_filters()
