import customtkinter as ctk
import tkinter as tk
import json
import time
import os
import sys
from tkinter import messagebox
from config import COLORS, FONTS, DEPARTMENTS

# Double all font sizes for task_updater_app
FONTS = {
    key: (val[0], val[1] * 2, *val[2:]) if isinstance(val, (tuple, list)) else val
    for key, val in FONTS.items()
}
from services.n8n_client import N8nClient
from services.sheets_client import SheetsClient
from services.extension_store import (
    submit_extension_request,
    get_requests_for_employee,
)
from tkcalendar import DateEntry
from datetime import datetime

# Resolve paths relative to exe directory when frozen
if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

CACHE_FILE = os.path.join(_APP_DIR, "recent_task_updates.json")

def format_date(date_str):
    if not date_str or date_str in ("N/A", "None", ""):
        return "N/A"
    s = str(date_str).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%d %b %Y")
        except ValueError:
            pass
    return s

def load_recent_updates():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                # Keep updates for 10 minutes to mask Sheets cache delay
                current_time = time.time()
                return {k: v for k, v in data.items() if current_time - v.get("timestamp", 0) < 600}
    except Exception:
        pass
    return {}

def save_recent_updates(updates_dict):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(updates_dict, f)
    except Exception:
        pass

class TaskUpdaterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Light")
        self.title("Stauff - Update Task Status")
        self.geometry("900x800")
        self.configure(fg_color=COLORS["bg"])

        try:
            self.iconbitmap(os.path.join(_APP_DIR, "user.ico"))
        except Exception:
            pass

        self.n8n_client = N8nClient()
        self.sheets_client = SheetsClient()
        
        self.departments = DEPARTMENTS
        self.current_tasks = []
        self.status_vars = {} # maps task_id to tk.StringVar
        self.modified_task_info = {} # maps task_id to dict of modifications
        
        self.current_dept = None
        self.current_user = None

        self.setup_login_ui()

    def setup_login_ui(self):
        self.login_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.login_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        card = ctk.CTkFrame(self.login_frame, fg_color=COLORS["card_bg"], corner_radius=8)
        card.place(relx=0.5, rely=0.5, anchor="center")
        
        lbl_title = ctk.CTkLabel(card, text="Welcome", font=FONTS["header"], text_color=COLORS["text_main"])
        lbl_title.pack(pady=(30, 10), padx=50)
        
        lbl_inst = ctk.CTkLabel(card, text="Please select your department and name", font=FONTS["body"], text_color=COLORS["text_dim"])
        lbl_inst.pack(pady=(0, 20), padx=50)
        
        self.login_combo_dept = ctk.CTkComboBox(card, values=list(self.departments.keys()), command=self.on_login_dept_select, width=400, height=48, font=FONTS["body"], dropdown_font=FONTS["body"], corner_radius=8, button_color=COLORS["accent"], dropdown_hover_color=COLORS["accent"])
        self.login_combo_dept.pack(pady=(0, 15), padx=50)
        
        self.login_combo_person = ctk.CTkComboBox(card, values=[], width=400, height=48, font=FONTS["body"], dropdown_font=FONTS["body"], corner_radius=8, button_color=COLORS["accent"], dropdown_hover_color=COLORS["accent"])
        self.login_combo_person.pack(pady=(0, 25), padx=50)
        
        btn_login = ctk.CTkButton(card, text="Continue", font=FONTS["body_bold"], fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self.do_login, width=400, height=48)
        btn_login.pack(pady=(0, 30), padx=50)
        
        if list(self.departments.keys()):
            self.login_combo_dept.set(list(self.departments.keys())[0])
            self.on_login_dept_select(self.login_combo_dept.get())

    def on_login_dept_select(self, dept):
        people = self.departments.get(dept, [])
        self.login_combo_person.configure(values=people)
        if people:
            self.login_combo_person.set(people[0])
        else:
            self.login_combo_person.set("")

    def do_login(self):
        dept = self.login_combo_dept.get()
        person = self.login_combo_person.get()
        if not dept or not person:
            messagebox.showwarning("Missing Info", "Please select both department and name.")
            return
            
        self.current_dept = dept
        self.current_user = person
        
        self.login_frame.destroy()
        self.setup_main_ui()

    def setup_main_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # ── Task Status Update Card ──
        card_tasks = ctk.CTkFrame(container, fg_color=COLORS["card_bg"], corner_radius=8)
        card_tasks.pack(fill="both", expand=True)

        lbl_tasks = ctk.CTkLabel(card_tasks, text="Update Live Task Status", font=FONTS["header"], text_color=COLORS["text_main"])
        lbl_tasks.pack(anchor="w", padx=20, pady=(20, 10))

        filter_frame = ctk.CTkFrame(card_tasks, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(filter_frame, text=f"Department: {self.current_dept}", font=FONTS["body_bold"], text_color=COLORS["text_main"]).pack(side="left", padx=(0, 20))
        ctk.CTkLabel(filter_frame, text=f"User: {self.current_user}", font=FONTS["body_bold"], text_color=COLORS["text_main"]).pack(side="left")

        # Scrollable area for tasks
        self.tasks_scroll = ctk.CTkScrollableFrame(card_tasks, fg_color="transparent")
        self.tasks_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        self.tasks_scroll.grid_columnconfigure(0, weight=1)

        self.btn_submit_updates = ctk.CTkButton(card_tasks, text="Update Statuses Directly", font=FONTS["body_bold"], fg_color=COLORS["success"], hover_color="#218c53", height=40, command=self.submit_updates_only)
        self.btn_submit_updates.pack(fill="x", padx=20, pady=(10, 10))

        # ── Extension Requests Card ──
        card_ext = ctk.CTkFrame(container, fg_color=COLORS["card_bg"], corner_radius=8)
        card_ext.pack(fill="x", pady=(15, 0))

        ext_header = ctk.CTkFrame(card_ext, fg_color="transparent")
        ext_header.pack(fill="x", padx=20, pady=(15, 5))

        lbl_ext = ctk.CTkLabel(ext_header, text="My Extension Requests", font=FONTS["subheader"], text_color=COLORS["text_main"])
        lbl_ext.pack(side="left")

        self.btn_refresh_ext = ctk.CTkButton(ext_header, text="↻ Refresh", width=80,
                                             font=FONTS["small"], fg_color=COLORS["accent"],
                                             hover_color=COLORS["accent_hover"], height=28,
                                             command=self._refresh_extension_list)
        self.btn_refresh_ext.pack(side="right")

        self.ext_scroll = ctk.CTkScrollableFrame(card_ext, fg_color="transparent", height=160)
        self.ext_scroll.pack(fill="x", padx=10, pady=(5, 15))
        self.ext_scroll.grid_columnconfigure(0, weight=1)

        self.fetch_tasks(self.current_user)
        self._refresh_extension_list()

    def fetch_tasks(self, person_name):
        if not person_name:
            return

        try:
            tasks = self.sheets_client.fetch_tasks_for_employee(person_name)
            
            # Apply recent local updates to mask Google Sheets cache delay
            recent_updates = load_recent_updates()
            for t in tasks:
                if t.task_id in recent_updates:
                    t.status = recent_updates[t.task_id]["status"]
                    if "reason" in recent_updates[t.task_id]:
                        t.reason = recent_updates[t.task_id]["reason"]

            active_tasks = [t for t in tasks if t.status.lower() not in ["completed", "done"]]
            self.current_tasks = active_tasks
            
            self.render_tasks()

        except Exception as e:
            # Clear existing on error
            for widget in self.tasks_scroll.winfo_children():
                widget.destroy()
            ctk.CTkLabel(self.tasks_scroll, text=f"Failed to fetch tasks.\n{e}", font=FONTS["body"], text_color=COLORS["error"]).pack(pady=20)

    def render_tasks(self):
        for widget in self.tasks_scroll.winfo_children():
            widget.destroy()
        self.status_vars.clear()
        self.modified_task_info.clear()
        
        person_name = self.current_user
        
        # Filter active tasks based on current_tasks state (which may have been updated locally)
        active_tasks = [t for t in self.current_tasks if t.status.lower() not in ["completed", "done"]]
        self.current_tasks = active_tasks

        # Fetch extensions to find approved new deadlines
        ext_requests = get_requests_for_employee(person_name)
        approved_extensions = {}
        for req in ext_requests:
            if req.get("status") == "Approved":
                approved_extensions[req["task_id"]] = req.get("manager_deadline") or req.get("requested_deadline")

        if not active_tasks:
            ctk.CTkLabel(self.tasks_scroll, text="No active tasks found.", font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=20)
        else:
            for idx, task in enumerate(active_tasks):
                row = ctk.CTkFrame(self.tasks_scroll, fg_color=COLORS["input_bg"], border_color=COLORS["border"], border_width=1, corner_radius=6)
                row.grid(row=idx, column=0, sticky="ew", pady=5, padx=5)
                row.grid_columnconfigure(0, weight=1)

                def bind_double_click(widget, t=task):
                    widget.bind("<Double-1>", lambda event, tk=t: self.show_task_details_dialog(tk))
                
                bind_double_click(row)
                
                info_frame = ctk.CTkFrame(row, fg_color="transparent")
                info_frame.grid(row=0, column=0, sticky="w", padx=10, pady=10)
                bind_double_click(info_frame)

                lbl_desc = ctk.CTkLabel(info_frame, text=f"[{task.task_id}] {task.description}", font=FONTS["body_bold"], text_color=COLORS["text_main"], justify="left", wraplength=1200)
                lbl_desc.pack(anchor="w")
                bind_double_click(lbl_desc)
                
                original_deadline = task.deadline
                current_deadline = approved_extensions.get(task.task_id, task.deadline)
                is_extended = task.task_id in approved_extensions
                
                task._current_deadline = current_deadline
                task._original_deadline = original_deadline
                task._is_extended = is_extended
                
                dl_str = format_date(current_deadline)
                if is_extended:
                    dl_str += " (Extended)"
                
                dates_str = f"Assigned: {format_date(task.date)}  |  Deadline: {dl_str}"
                lbl_dates = ctk.CTkLabel(info_frame, text=dates_str, font=FONTS["small"], text_color=COLORS["text_dim"])
                lbl_dates.pack(anchor="w", pady=(4, 0))
                bind_double_click(lbl_dates)

                if current_deadline:
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y"):
                        try:
                            dl_date = datetime.strptime(str(current_deadline).strip(), fmt).date()
                            today = datetime.now().date()
                            days_past = (today - dl_date).days
                            if days_past > 0:
                                lbl_timer = ctk.CTkLabel(info_frame, text=f"⚠ {days_past} days past deadline!", font=FONTS["small"], text_color=COLORS["error"])
                                lbl_timer.pack(anchor="w")
                                bind_double_click(lbl_timer)
                            break
                        except ValueError:
                            pass

                var = ctk.StringVar(value=task.status)
                self.status_vars[task.task_id] = var
                
                def on_status_change(new_val, t=task, v=var):
                    if new_val == "Delayed":
                        self.prompt_extension_request(t, v)
                    else:
                        # If changed back from Delayed, clear the modified info
                        if t.task_id in self.modified_task_info:
                            del self.modified_task_info[t.task_id]

                combo = ctk.CTkComboBox(
                    row,
                    values=["Pending", "Delayed", "Completed"],
                    variable=var,
                    width=240,
                    height=48,
                    font=FONTS["body_bold"],
                    dropdown_font=FONTS["body"],
                    corner_radius=8,
                    button_color=COLORS["accent"],
                    button_hover_color=COLORS["accent_hover"],
                    dropdown_hover_color=COLORS["accent"],
                    dropdown_fg_color=COLORS["card_bg"],
                    dropdown_text_color=COLORS["text_main"],
                    command=on_status_change
                )
                combo.grid(row=0, column=1, padx=15, pady=10)

    def show_task_details_dialog(self, task):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Task Details: {task.task_id}")
        dialog.geometry("500x600")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (500 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (600 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        details = [
            ("Task ID", task.task_id),
            ("Date Assigned", format_date(task.date)),
            ("Current Deadline", format_date(getattr(task, "_current_deadline", task.deadline)) + (" (Extended)" if getattr(task, "_is_extended", False) else "")),
        ]
        
        if getattr(task, "_is_extended", False):
            details.append(("Original Deadline", format_date(getattr(task, "_original_deadline", "N/A"))))
            
        details.extend([
            ("Assigned To", task.assigned_to),
            ("Assigned By", task.assigned_by),
            ("Priority", task.priority),
            ("Status", task.status),
            ("Reason", task.reason),
            ("Source", task.source),
            ("Last Updated", task.last_updated),
        ])
        
        for label, value in details:
            lbl_title = ctk.CTkLabel(scroll, text=f"{label}:", font=FONTS["body_bold"], text_color=COLORS["text_main"])
            lbl_title.pack(anchor="w", pady=(10, 0))
            
            lbl_val = ctk.CTkLabel(scroll, text=str(value) if value else "N/A", font=FONTS["body"], text_color=COLORS["text_dim"], wraplength=450, justify="left")
            lbl_val.pack(anchor="w")

        lbl_desc_title = ctk.CTkLabel(scroll, text="Description:", font=FONTS["body_bold"], text_color=COLORS["text_main"])
        lbl_desc_title.pack(anchor="w", pady=(10, 0))
        
        desc_box = ctk.CTkTextbox(scroll, height=120, font=FONTS["body"], text_color=COLORS["text_dim"], fg_color=COLORS["input_bg"])
        desc_box.insert("1.0", str(task.description))
        desc_box.configure(state="disabled")
        desc_box.pack(fill="x", pady=(5, 10))
        
        btn_close = ctk.CTkButton(dialog, text="Close", command=dialog.destroy, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
        btn_close.pack(pady=20)

    def prompt_extension_request(self, task, var):
        """Show a dialog for the employee to request a deadline extension."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Request Deadline Extension")
        dialog.geometry("430x400")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (430 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (400 // 2)
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text=f"Task: [{task.task_id}]", font=FONTS["body_bold"],
                     text_color=COLORS["text_main"]).pack(pady=(20, 2), padx=20, anchor="w")
        ctk.CTkLabel(dialog, text=f"Current Deadline: {format_date(task.deadline)}",
                     font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=(0, 10), padx=20, anchor="w")

        ctk.CTkLabel(dialog, text="Reason for Extension:", font=FONTS["body_bold"]).pack(pady=(10, 5), padx=20, anchor="w")
        reason_text = ctk.CTkTextbox(dialog, height=80)
        reason_text.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(dialog, text="Requested New Deadline:", font=FONTS["body_bold"]).pack(pady=(10, 5), padx=20, anchor="w")
        
        deadline_entry = DateEntry(dialog, width=28, date_pattern='dd/mm/yyyy', background=COLORS["sidebar_bg"], foreground='white', borderwidth=2, font=FONTS["body"])
        deadline_entry.pack(padx=20, pady=(0, 10), anchor="w")

        ctk.CTkLabel(dialog, text="⚠ Your request will be sent to the manager for approval.",
                     font=FONTS["small"], text_color=COLORS["warning"]).pack(padx=20, pady=(0, 10), anchor="w")

        def submit():
            reason = reason_text.get("1.0", "end").strip()
            new_deadline = deadline_entry.get()
            
            if not reason:
                messagebox.showwarning("Missing Info", "Please provide a reason for the extension.")
                return

            # Submit extension request to shared store
            person_name = self.current_user
            req_id = submit_extension_request(
                task_id=task.task_id,
                task_description=task.description,
                employee_name=person_name,
                current_deadline=task.deadline,
                requested_deadline=new_deadline,
                reason=reason,
            )

            # Mark the task as Delayed with the reason (but no deadline change yet)
            self.modified_task_info[task.task_id] = {
                "reason": f"{reason} (Old Deadline: {task.deadline}) [Extension Request: {req_id}]",
                "deadline": task.deadline  # Keep the old deadline — manager decides
            }
            dialog.destroy()
            messagebox.showinfo("Request Sent",
                                f"Extension request [{req_id}] has been submitted.\n"
                                "The manager will review it on the dashboard.")
            self._refresh_extension_list()
            
        def cancel():
            var.set(task.status)
            dialog.destroy()
            
        dialog.protocol("WM_DELETE_WINDOW", cancel)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkButton(btn_frame, text="Submit Request", command=submit, fg_color=COLORS["accent"], width=120).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_frame, text="Cancel", command=cancel, fg_color="transparent", border_width=1, text_color=("gray20", "white"), hover_color=("gray85", "gray30"), width=100).pack(side="right")

    # ── Extension Requests Display ───────────────────────────────────

    def _refresh_extension_list(self):
        """Refresh the extension requests list for the currently selected employee."""
        for w in self.ext_scroll.winfo_children():
            w.destroy()

        person = self.current_user
        if not person:
            return

        requests = get_requests_for_employee(person)
        if not requests:
            ctk.CTkLabel(self.ext_scroll, text="No extension requests yet.",
                         font=FONTS["small"], text_color=COLORS["text_dim"]).pack(pady=10)
            return

        # Show most recent first
        for idx, req in enumerate(reversed(requests)):
            status = req["status"]
            if status == "Pending":
                badge_color = COLORS["warning"]
                badge_text = "⏳ Pending"
            elif status == "Approved":
                badge_color = COLORS["success"]
                badge_text = "✓ Approved"
            else:
                badge_color = COLORS["error"]
                badge_text = "✗ Rejected"

            row = ctk.CTkFrame(self.ext_scroll, fg_color=COLORS["input_bg"], border_color=COLORS["border"], border_width=1, corner_radius=6)
            row.grid(row=idx, column=0, sticky="ew", pady=3, padx=5)
            row.grid_columnconfigure(1, weight=1)

            # Status badge
            badge = ctk.CTkLabel(row, text=badge_text, font=FONTS["small"],
                                 text_color="white", fg_color=badge_color,
                                 corner_radius=4, width=90, height=24)
            badge.grid(row=0, column=0, padx=(10, 5), pady=8)

            # Task info
            desc = req["task_description"]
            if len(desc) > 50:
                desc = desc[:50] + "..."
            info_text = f"[{req['task_id']}] {desc}"
            ctk.CTkLabel(row, text=info_text, font=FONTS["small"],
                         text_color=COLORS["text_main"]).grid(row=0, column=1, sticky="w", padx=5, pady=8)

            # Deadline info
            if status == "Approved":
                final_deadline = format_date(req.get("manager_deadline") or req["requested_deadline"])
                dl_text = f"New Deadline: {final_deadline}"
                dl_color = COLORS["success"]
            elif status == "Rejected":
                dl_text = f"Deadline unchanged: {format_date(req['current_deadline'])}"
                dl_color = COLORS["error"]
            else:
                dl_text = f"Requested: {format_date(req['requested_deadline'])}"
                dl_color = COLORS["text_dim"]

            ctk.CTkLabel(row, text=dl_text, font=FONTS["small"],
                         text_color=dl_color).grid(row=0, column=2, padx=(5, 10), pady=8)

            # Show manager note if decided
            if status != "Pending" and req.get("manager_note"):
                note_row = ctk.CTkFrame(self.ext_scroll, fg_color="transparent")
                note_row.grid(row=idx * 2 + 1, column=0, sticky="ew", padx=20, pady=(0, 3))
                ctk.CTkLabel(note_row, text=f"Manager note: {req['manager_note']}",
                             font=FONTS["small"], text_color=COLORS["text_dim"]).pack(anchor="w")

    # ── Submit Updates ───────────────────────────────────────────────

    def submit_updates_only(self):
        # Build list of modified tasks
        modified_tasks = []
        for task in self.current_tasks:
            new_status = self.status_vars.get(task.task_id).get()
            if new_status != task.status:
                mod_info = self.modified_task_info.get(task.task_id, {})
                task_dict = {
                    "Task ID": task.task_id,
                    "Date": task.date,
                    "Task Description": task.description,
                    "Assigned To": task.assigned_to,
                    "Assigned By": task.assigned_by,
                    "Deadline": mod_info.get("deadline", task.deadline),
                    "Priority": task.priority,
                    "Status": new_status,  # Updated status
                    "Reason": mod_info.get("reason", task.reason),
                    "Source": task.source,
                    "Updated By": "UI Input",
                    "Last Updated": task.last_updated
                }
                modified_tasks.append(task_dict)

        if not modified_tasks:
            messagebox.showinfo("Info", "No task statuses were changed.")
            return

        self.btn_submit_updates.configure(state="disabled")
        try:
            # Send to webhook
            success = self.n8n_client.submit_live_updates(modified_tasks)
            if success:
                messagebox.showinfo("Success", "Task statuses updated successfully.")
                
                # Update local tasks state and cache to avoid the 5-minute Google Sheets published CSV cache
                recent_updates = load_recent_updates()
                
                for task_dict in modified_tasks:
                    # Save to cache file
                    recent_updates[task_dict["Task ID"]] = {
                        "status": task_dict["Status"],
                        "reason": task_dict.get("Reason", ""),
                        "timestamp": time.time()
                    }
                    
                    # Update active state
                    for task in self.current_tasks:
                        if task.task_id == task_dict["Task ID"]:
                            task.status = task_dict["Status"]
                            if "Reason" in task_dict:
                                task.reason = task_dict["Reason"]
                            break
                            
                save_recent_updates(recent_updates)
                            
                # Re-render UI with the updated local tasks
                self.render_tasks()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update tasks:\n{e}")
        finally:
            self.btn_submit_updates.configure(state="normal")

if __name__ == "__main__":
    app = TaskUpdaterApp()
    app.mainloop()
