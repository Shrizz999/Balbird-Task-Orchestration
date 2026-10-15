"""
Task Assignment View — brings the four task-assignment screens from the
standalone app.py into the Dashboard as a single view with sub-tabs.

The four screens are:
  1. Daily Goals         (create daily individual goals)
  2. Department Goals    (create monthly department goals)
  3. Meeting Updates     (send transcript to n8n)
  4. Monthly Task Updater (update monthly department task status)

All logic and visuals are preserved exactly from the original files.
"""

import sys
import os
from pathlib import Path

# Ensure the root project directory is on sys.path so that
# `from config import ...` and `from services.xxx import ...` work.
if getattr(sys, 'frozen', False):
    _ROOT_DIR = str(Path(sys.executable).resolve().parent)
else:
    _ROOT_DIR = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

import customtkinter as ctk
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
import threading

import config
from config import COLORS, FONTS, ALL_EMPLOYEES, ALL_DEPARTMENTS, DEPARTMENTS, SHOW_MEETING_TRANSCRIPTS
from services.n8n_client import N8nClient
from services.supabase_client import SupabaseClient
from tkcalendar import DateEntry

from .components import BG_COLOR, CARD_BG, BORDER_COLOR, TEXT_COLOR, TEXT_MUTED, ACCENT_COLOR
from data.repository import DataRepository


# ═══════════════════════════════════════════════════════════════════════════
# Sub-frame 1: Daily Goals
# ═══════════════════════════════════════════════════════════════════════════

class DailyGoalsSubFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.n8n_client = N8nClient()
        self.setup_ui()

    def setup_ui(self):
        lbl_header = ctk.CTkLabel(self, text="Create Daily Individual Goal", font=FONTS["header"], text_color=COLORS["text_main"])
        lbl_header.pack(anchor="w", pady=(0, 20))

        form_frame = ctk.CTkFrame(self, fg_color=COLORS["card_bg"], corner_radius=8)
        form_frame.pack(fill="x", pady=10)

        # Employee
        ctk.CTkLabel(form_frame, text="Employee", font=FONTS["body_bold"], text_color=COLORS["text_main"]).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.combo_employee = ctk.CTkComboBox(form_frame, values=ALL_EMPLOYEES, width=300)
        self.combo_employee.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="w")
        if ALL_EMPLOYEES:
            self.combo_employee.set(ALL_EMPLOYEES[0])

        # Goal Date
        ctk.CTkLabel(form_frame, text="Goal Date", font=FONTS["body_bold"], text_color=COLORS["text_main"]).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.entry_date = DateEntry(form_frame, width=28, date_pattern='dd/mm/yyyy', background=COLORS["sidebar_bg"], foreground='white', borderwidth=2, font=FONTS["body"])
        self.entry_date.grid(row=1, column=1, padx=20, pady=10, sticky="w")

        # Deadline
        ctk.CTkLabel(form_frame, text="Deadline", font=FONTS["body_bold"], text_color=COLORS["text_main"]).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.entry_deadline = DateEntry(form_frame, width=28, date_pattern='dd/mm/yyyy', background=COLORS["sidebar_bg"], foreground='white', borderwidth=2, font=FONTS["body"])
        self.entry_deadline.grid(row=2, column=1, padx=20, pady=10, sticky="w")

        # Priority
        ctk.CTkLabel(form_frame, text="Priority", font=FONTS["body_bold"], text_color=COLORS["text_main"]).grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.combo_priority = ctk.CTkComboBox(form_frame, values=["Low", "Normal", "High", "Urgent"], width=300)
        self.combo_priority.set("Normal")
        self.combo_priority.grid(row=3, column=1, padx=20, pady=10, sticky="w")

        # Goal Description
        ctk.CTkLabel(form_frame, text="Goal Description", font=FONTS["body_bold"], text_color=COLORS["text_main"]).grid(row=4, column=0, padx=20, pady=10, sticky="nw")
        self.text_goal = ctk.CTkTextbox(form_frame, width=300, height=100)
        self.text_goal.grid(row=4, column=1, padx=20, pady=10, sticky="w")

        # Submit
        self.btn_submit = ctk.CTkButton(form_frame, text="Submit Daily Goal", font=FONTS["body_bold"], fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self.submit_goal)
        self.btn_submit.grid(row=5, column=1, padx=20, pady=(10, 20), sticky="e")

    def submit_goal(self):
        emp = self.combo_employee.get()
        date = self.entry_date.get()
        deadline = self.entry_deadline.get()
        priority = self.combo_priority.get()
        goal_text = self.text_goal.get("1.0", "end").strip()

        if not emp or not date or not deadline or not goal_text:
            messagebox.showwarning("Missing Fields", "Please fill in all fields including the deadline.")
            return

        payload = {
            emp: [
                {
                    "goal": goal_text,
                    "date": date,
                    "deadline": deadline,
                    "priority": priority
                }
            ]
        }

        self.btn_submit.configure(state="disabled")
        try:
            success = self.n8n_client.submit_daily_goals(payload)
            if success:
                messagebox.showinfo("Success", "Daily goal successfully submitted to n8n.")
                self.text_goal.delete("1.0", "end")
                self.entry_deadline.set_date(datetime.now())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit goal:\n{e}")
        finally:
            self.btn_submit.configure(state="normal")


# ═══════════════════════════════════════════════════════════════════════════
# Sub-frame 2: Department Goals
# ═══════════════════════════════════════════════════════════════════════════

class DepartmentGoalsSubFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.n8n_client = N8nClient()
        self.setup_ui()

    def setup_ui(self):
        lbl_header = ctk.CTkLabel(self, text="Create Department Monthly Goal", font=FONTS["header"], text_color=COLORS["text_main"])
        lbl_header.pack(anchor="w", pady=(0, 20))

        form_frame = ctk.CTkFrame(self, fg_color=COLORS["card_bg"], corner_radius=8)
        form_frame.pack(fill="x", pady=10)

        # Department
        ctk.CTkLabel(form_frame, text="Department", font=FONTS["body_bold"], text_color=COLORS["text_main"]).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.combo_dept = ctk.CTkComboBox(form_frame, values=ALL_DEPARTMENTS, width=300)
        self.combo_dept.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="w")
        if ALL_DEPARTMENTS:
            self.combo_dept.set(ALL_DEPARTMENTS[0])

        # Month
        ctk.CTkLabel(form_frame, text="Target Month", font=FONTS["body_bold"], text_color=COLORS["text_main"]).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        month_str = datetime.now().strftime("%B %Y")
        self.entry_month = ctk.CTkEntry(form_frame, width=300, placeholder_text="e.g. September 2026")
        self.entry_month.insert(0, month_str)
        self.entry_month.grid(row=1, column=1, padx=20, pady=10, sticky="w")

        # Deadline
        ctk.CTkLabel(form_frame, text="Deadline", font=FONTS["body_bold"], text_color=COLORS["text_main"]).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.entry_deadline = DateEntry(form_frame, width=28, date_pattern='dd/mm/yyyy', background=COLORS["sidebar_bg"], foreground='white', borderwidth=2, font=FONTS["body"])
        self.entry_deadline.grid(row=2, column=1, padx=20, pady=10, sticky="w")

        # Goal Description
        ctk.CTkLabel(form_frame, text="Monthly Goal", font=FONTS["body_bold"], text_color=COLORS["text_main"]).grid(row=3, column=0, padx=20, pady=10, sticky="nw")
        self.text_goal = ctk.CTkTextbox(form_frame, width=300, height=100)
        self.text_goal.grid(row=3, column=1, padx=20, pady=10, sticky="w")

        # Submit
        self.btn_submit = ctk.CTkButton(form_frame, text="Submit Monthly Goal", font=FONTS["body_bold"], fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self.submit_goal)
        self.btn_submit.grid(row=4, column=1, padx=20, pady=(10, 20), sticky="e")

    def submit_goal(self):
        dept = self.combo_dept.get()
        month = self.entry_month.get()
        deadline = self.entry_deadline.get()
        goal_text = self.text_goal.get("1.0", "end").strip()

        if not dept or not month or not deadline or not goal_text:
            messagebox.showwarning("Missing Fields", "Please fill in all fields.")
            return

        payload = {
            dept: {
                "goal": goal_text,
                "month": month,
                "deadline": deadline
            }
        }

        self.btn_submit.configure(state="disabled")
        try:
            success = self.n8n_client.submit_monthly_goals(payload)
            if success:
                messagebox.showinfo("Success", "Monthly goal successfully submitted to n8n.")
                self.text_goal.delete("1.0", "end")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit goal:\n{e}")
        finally:
            self.btn_submit.configure(state="normal")


# ═══════════════════════════════════════════════════════════════════════════
# Sub-frame 3: Meeting Updates (Transcript)
# ═══════════════════════════════════════════════════════════════════════════

class MeetingUpdatesSubFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.n8n_client = N8nClient()
        self.setup_ui()

    def setup_ui(self):
        lbl_header = ctk.CTkLabel(self, text="Meeting Transcript", font=FONTS["header"], text_color=COLORS["text_main"])
        lbl_header.pack(anchor="w", pady=(0, 20))

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)

        # ── Left: Transcript ──
        card_transcript = ctk.CTkFrame(container, fg_color=COLORS["card_bg"], corner_radius=8)
        card_transcript.grid(row=0, column=0, sticky="nsew")

        lbl_transcript = ctk.CTkLabel(card_transcript, text="Meeting Transcript", font=FONTS["subheader"], text_color=COLORS["text_main"])
        lbl_transcript.pack(anchor="w", padx=20, pady=(20, 10))

        self.text_transcript = ctk.CTkTextbox(card_transcript, height=300)
        self.text_transcript.pack(fill="both", expand=True, padx=20, pady=10)

        btn_row = ctk.CTkFrame(card_transcript, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))
        
        self.btn_browse = ctk.CTkButton(btn_row, text="Browse .txt", width=120, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self.browse_file)
        self.btn_browse.pack(side="left")

        self.btn_clear = ctk.CTkButton(btn_row, text="Clear", width=100, fg_color="transparent", text_color=COLORS["text_main"], border_width=1, command=lambda: self.text_transcript.delete("1.0", "end"))
        self.btn_clear.pack(side="right")

        self.btn_submit_transcript = ctk.CTkButton(card_transcript, text="Send Transcript to n8n", font=FONTS["body_bold"], fg_color=COLORS["highlight"], hover_color=COLORS["highlight_hover"], height=40, command=self.submit_transcript_only)
        self.btn_submit_transcript.pack(fill="x", padx=20, pady=(0, 20))

    def browse_file(self):
        path = filedialog.askopenfilename(title="Select Transcript", filetypes=[("Text files", "*.txt")])
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.text_transcript.delete("1.0", "end")
                    self.text_transcript.insert("1.0", f.read())
            except Exception as e:
                messagebox.showerror("File Error", f"Could not read file:\n{e}")

    def submit_transcript_only(self):
        transcript = self.text_transcript.get("1.0", "end").strip()
        if not transcript:
            messagebox.showwarning("Missing Info", "No transcript provided.")
            return

        self.btn_submit_transcript.configure(state="disabled")
        try:
            success = self.n8n_client.submit_transcript(transcript)
            if success:
                messagebox.showinfo("Success", "Transcript successfully sent to n8n.")
                self.text_transcript.delete("1.0", "end")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit transcript:\n{e}")
        finally:
            self.btn_submit_transcript.configure(state="normal")


# ═══════════════════════════════════════════════════════════════════════════
# Sub-frame 4: Monthly Task Updater
# ═══════════════════════════════════════════════════════════════════════════

class MonthlyTaskUpdaterSubFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        
        self.n8n_client = N8nClient()
        self.sheets_client = SupabaseClient()
        
        self.departments = list(DEPARTMENTS.keys())
        self.current_goals = []
        self.status_vars = {} # maps goal_id to tk.StringVar
        self.modified_goal_info = {} # maps goal_id to dict of modifications
        self.recently_updated_status = {} # locally track status updates to bypass cache delay

        self.setup_ui()

    def setup_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        card_tasks = ctk.CTkFrame(container, fg_color=COLORS["card_bg"], corner_radius=8)
        card_tasks.pack(fill="both", expand=True)

        lbl_tasks = ctk.CTkLabel(card_tasks, text="Update Monthly Department Tasks Status", font=FONTS["header"], text_color=COLORS["text_main"])
        lbl_tasks.pack(anchor="w", padx=20, pady=(20, 10))

        filter_frame = ctk.CTkFrame(card_tasks, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=10)

        self.combo_dept = ctk.CTkComboBox(filter_frame, values=self.departments, command=self.fetch_tasks)
        self.combo_dept.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        # Scrollable area for tasks
        self.tasks_scroll = ctk.CTkScrollableFrame(card_tasks, fg_color="transparent")
        self.tasks_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        self.tasks_scroll.grid_columnconfigure(0, weight=1)

        self.btn_submit_updates = ctk.CTkButton(card_tasks, text="Update Statuses Directly", font=FONTS["body_bold"], fg_color=COLORS["success"], hover_color="#218c53", height=40, command=self.submit_updates_only)
        self.btn_submit_updates.pack(fill="x", padx=20, pady=20)

    def load_data(self):
        if self.departments:
            self.combo_dept.set(self.departments[0])
            self.fetch_tasks(self.combo_dept.get())

    def fetch_tasks(self, dept_name):
        # Clear existing
        for widget in self.tasks_scroll.winfo_children():
            widget.destroy()
        self.status_vars.clear()
        self.current_goals.clear()
        self.modified_goal_info.clear()

        if not dept_name:
            return

        self.combo_dept.configure(state="disabled")

        # Show loading message
        loading_lbl = ctk.CTkLabel(self.tasks_scroll, text="Loading tasks...", font=FONTS["body"], text_color=COLORS["text_dim"])
        loading_lbl.pack(pady=20)

        def fetch_thread():
            try:
                goals = self.sheets_client.fetch_monthly_goals()
                self.after(0, self.update_tasks_ui, dept_name, goals, loading_lbl)
            except Exception as e:
                self.after(0, self.show_error, str(e), loading_lbl)

        threading.Thread(target=fetch_thread, daemon=True).start()

    def update_tasks_ui(self, dept_name, goals, loading_lbl):
        loading_lbl.destroy()
        
        # Filter uncompleted tasks for the specific department
        active_goals = []
        for g in goals:
            if g.assigned_to == dept_name:
                # Override status if we updated it recently and it hasn't caught up
                actual_status = self.recently_updated_status.get(g.goal_id, g.status)
                if actual_status.lower() not in ["completed", "done", "update"]:
                    active_goals.append(g)

        self.current_goals = active_goals

        if not active_goals:
            ctk.CTkLabel(self.tasks_scroll, text="No active monthly tasks found.", font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=20)
        else:
            for idx, goal in enumerate(active_goals):
                row = ctk.CTkFrame(self.tasks_scroll, fg_color=COLORS["input_bg"], corner_radius=6)
                row.grid(row=idx, column=0, sticky="ew", pady=5, padx=5)
                row.grid_columnconfigure(0, weight=1)

                info_frame = ctk.CTkFrame(row, fg_color="transparent")
                info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
                
                desc = goal.goal if len(goal.goal) < 120 else goal.goal[:120] + "..."
                title_lbl = ctk.CTkLabel(info_frame, text=f"[{goal.goal_id}] {desc}", font=FONTS["body_bold"], text_color=COLORS["text_main"], justify="left", wraplength=550)
                title_lbl.pack(anchor="w", pady=(0, 6))

                footer_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
                footer_frame.pack(anchor="w", fill="x")

                def add_badge(parent, text):
                    lbl = ctk.CTkLabel(parent, text=f"  {text}  ", font=FONTS["small"], text_color=COLORS["text_dim"], fg_color=COLORS["bg"], corner_radius=4, height=20)
                    lbl.pack(side="left", padx=(0, 8))

                add_badge(footer_frame, f"Month: {goal.week_month}")
                add_badge(footer_frame, f"Deadline: {goal.deadline}")
                add_badge(footer_frame, f"Priority: {goal.priority}")
                add_badge(footer_frame, f"Given By: {goal.given_by}")

                actual_status = self.recently_updated_status.get(goal.goal_id, goal.status)
                var = ctk.StringVar(value=actual_status)
                self.status_vars[goal.goal_id] = var
                
                def on_status_change(new_val, g=goal, v=var):
                    if new_val == "Delayed":
                        self.prompt_delay_info(g, v)
                    else:
                        # If changed back from Delayed, clear the modified info
                        if g.goal_id in self.modified_goal_info:
                            del self.modified_goal_info[g.goal_id]

                combo = ctk.CTkComboBox(row, values=["Pending", "Delayed", "Completed"], variable=var, width=120, command=on_status_change)
                combo.grid(row=0, column=1, padx=10, pady=10)

        self.combo_dept.configure(state="normal")

    def show_error(self, error_msg, loading_lbl):
        loading_lbl.destroy()
        ctk.CTkLabel(self.tasks_scroll, text=f"Failed to fetch tasks.\n{error_msg}", font=FONTS["body"], text_color=COLORS["error"]).pack(pady=20)
        self.combo_dept.configure(state="normal")


    def prompt_delay_info(self, goal, var):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Delay Info")
        dialog.geometry("400x350")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (400 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (350 // 2)
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text="Reason for Delay:", font=FONTS["body_bold"]).pack(pady=(20, 5), padx=20, anchor="w")
        reason_text = ctk.CTkTextbox(dialog, height=80)
        reason_text.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(dialog, text="New Deadline:", font=FONTS["body_bold"]).pack(pady=(10, 5), padx=20, anchor="w")
        
        deadline_entry = DateEntry(dialog, width=28, date_pattern='dd/mm/yyyy', background=COLORS["sidebar_bg"], foreground='white', borderwidth=2, font=FONTS["body"])
        deadline_entry.pack(padx=20, pady=(0, 20), anchor="w")

        def submit():
            reason = reason_text.get("1.0", "end").strip()
            new_deadline = deadline_entry.get()
            
            if not reason:
                messagebox.showwarning("Missing Info", "Please provide a reason for the delay.")
                return
                
            self.modified_goal_info[goal.goal_id] = {
                "reason": f"{reason} (Old Deadline: {goal.deadline})",
                "deadline": new_deadline
            }
            dialog.destroy()
            
        def cancel():
            var.set(goal.status)
            dialog.destroy()
            
        dialog.protocol("WM_DELETE_WINDOW", cancel)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(btn_frame, text="Submit", command=submit, fg_color=COLORS["accent"], width=100).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_frame, text="Cancel", command=cancel, fg_color="transparent", border_width=1, text_color=("gray20", "white"), hover_color=("gray85", "gray30"), width=100).pack(side="right")

    def submit_updates_only(self):
        modified_goals = []
        for goal in self.current_goals:
            new_status = self.status_vars.get(goal.goal_id).get()
            if new_status != goal.status:
                mod_info = self.modified_goal_info.get(goal.goal_id, {})
                task_dict = {
                    "Task ID": goal.goal_id,
                    "Date": goal.week_month,
                    "Task Description": goal.goal,
                    "Assigned To": goal.assigned_to,
                    "Assigned By": goal.given_by,
                    "Deadline": mod_info.get("deadline", goal.deadline),
                    "Priority": goal.priority,
                    "Status": new_status,
                    "Reason": mod_info.get("reason", goal.reason),
                    "Source": "",
                    "Updated By": "UI Input",
                    "Last Updated": goal.last_updated
                }
                modified_goals.append(task_dict)

        if not modified_goals:
            messagebox.showinfo("Info", "No task statuses were changed.")
            return

        self.btn_submit_updates.configure(state="disabled")
        try:
            success = self.n8n_client.submit_goals_updates(modified_goals)
            if success:
                for task in modified_goals:
                    self.recently_updated_status[task["Task ID"]] = task["Status"]
                        
                messagebox.showinfo("Success", "Task statuses updated successfully.")
                self.fetch_tasks(self.combo_dept.get())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update tasks:\n{e}")
        finally:
            self.btn_submit_updates.configure(state="normal")


# ═══════════════════════════════════════════════════════════════════════════
# Main View: Task Assignment (with sub-tabs)
# ═══════════════════════════════════════════════════════════════════════════

class TaskAssignmentView(ctk.CTkFrame):
    """
    Top-level view shown in the Dashboard when the user clicks
    "Task Assignment" in the sidebar.  Contains four sub-tabs that
    map 1-to-1 with the original app.py navigation items.
    """

    def __init__(self, master, repository: DataRepository, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self.repository = repository  # kept for interface compatibility

        # Tab bar at the top
        self.tab_bar = ctk.CTkFrame(self, fg_color=CARD_BG, border_width=1,
                                     border_color=BORDER_COLOR, corner_radius=0)
        self.tab_bar.pack(fill="x")

        # Content area
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True)

        # Define sub-tabs (Meeting Updates / Transcript hidden when SHOW_MEETING_TRANSCRIPTS is False)
        self.sub_tabs = [
            ("Daily Goals", DailyGoalsSubFrame),
            ("Department Goals", DepartmentGoalsSubFrame),
        ]
        if getattr(config, "SHOW_MEETING_TRANSCRIPTS", False):
            self.sub_tabs.append(("Meeting Updates", MeetingUpdatesSubFrame))
        self.sub_tabs.append(("Monthly Task Updater", MonthlyTaskUpdaterSubFrame))

        self.tab_buttons = {}
        self.sub_frames = {}

        for idx, (label, frame_class) in enumerate(self.sub_tabs):
            btn = ctk.CTkButton(
                self.tab_bar, text=label,
                fg_color="transparent",
                text_color=TEXT_COLOR,
                hover_color=BG_COLOR,
                font=("Inter", 13, "bold"),
                corner_radius=0,
                height=40,
                command=lambda l=label: self._show_sub_tab(l)
            )
            btn.pack(side="left", padx=2, pady=4)
            self.tab_buttons[label] = btn

            frame_instance = frame_class(self.content)
            frame_instance.pack_forget()
            self.sub_frames[label] = frame_instance

        # Show first tab by default
        self._show_sub_tab("Daily Goals")

    def _show_sub_tab(self, label: str):
        # Update button highlights
        for name, btn in self.tab_buttons.items():
            if name == label:
                btn.configure(fg_color=ACCENT_COLOR, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_COLOR)

        # Swap visible frame
        for name, frame in self.sub_frames.items():
            frame.pack_forget()

        frame = self.sub_frames[label]
        if hasattr(frame, "load_data"):
            frame.load_data()
        frame.pack(fill="both", expand=True, padx=20, pady=20)

    def refresh_data(self):
        """Called by the Dashboard on auto-refresh / manual refresh."""
        # The sub-frames manage their own data via n8n/sheets clients,
        # so nothing special is needed here.
        pass

    def update_dropdowns(self):
        import config
        # Update Daily Goals dropdown
        if "Daily Goals" in self.sub_frames:
            daily = self.sub_frames["Daily Goals"]
            if hasattr(daily, "combo_employee"):
                daily.combo_employee.configure(values=config.ALL_EMPLOYEES)
                
        # Update Department Goals dropdown
        if "Department Goals" in self.sub_frames:
            dept = self.sub_frames["Department Goals"]
            if hasattr(dept, "combo_dept"):
                dept.combo_dept.configure(values=config.ALL_DEPARTMENTS)
                
        # Update Monthly Task Updater dropdown
        if "Monthly Task Updater" in self.sub_frames:
            monthly = self.sub_frames["Monthly Task Updater"]
            if hasattr(monthly, "combo_dept"):
                monthly.combo_dept.configure(values=config.ALL_DEPARTMENTS)

