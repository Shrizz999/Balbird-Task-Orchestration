import customtkinter as ctk
import tkinter as tk
import threading
from tkinter import messagebox
from config import COLORS, FONTS, DEPARTMENTS
from services.n8n_client import N8nClient
from services.supabase_client import SupabaseClient
from tkcalendar import DateEntry

class MonthlyTasksUpdatesFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.n8n_client = N8nClient()
        self.sheets_client = SupabaseClient()
        
        self.departments = list(DEPARTMENTS.keys())
        self.current_goals = []
        self.status_vars = {} # maps goal_id to tk.StringVar
        self.modified_goal_info = {} # maps goal_id to dict of modifications

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
        active_goals = [g for g in goals if g.assigned_to == dept_name and g.status.lower() not in ["completed", "done"]]
        self.current_goals = active_goals

        if not active_goals:
            ctk.CTkLabel(self.tasks_scroll, text="No active monthly tasks found.", font=FONTS["body"], text_color=COLORS["text_dim"]).pack(pady=20)
        else:
            for idx, goal in enumerate(active_goals):
                row = ctk.CTkFrame(self.tasks_scroll, fg_color=COLORS["input_bg"], corner_radius=6)
                row.grid(row=idx, column=0, sticky="ew", pady=5, padx=5)
                row.grid_columnconfigure(0, weight=1)

                desc = goal.goal if len(goal.goal) < 70 else goal.goal[:70] + "..."
                lbl = ctk.CTkLabel(row, text=f"[{goal.goal_id}] {desc}", font=FONTS["small"], text_color=COLORS["text_main"])
                lbl.grid(row=0, column=0, sticky="w", padx=10, pady=10)

                var = ctk.StringVar(value=goal.status)
                self.status_vars[goal.goal_id] = var
                
                # Add checklist button if checklist exists
                has_checklist = bool(getattr(goal, 'checklist', None))
                if has_checklist:
                    btn_checklist = ctk.CTkButton(row, text="Checklist", width=80, height=28, 
                                                  fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                                                  command=lambda g=goal: self.show_checklist_dialog(g))
                    btn_checklist.grid(row=0, column=1, padx=10, pady=10)
                
                def on_status_change(new_val, g=goal, v=var):
                    if new_val == "Delayed":
                        self.prompt_delay_info(g, v)
                    else:
                        # If changed back from Delayed, clear the modified info
                        if g.goal_id in self.modified_goal_info:
                            del self.modified_goal_info[g.goal_id]

                combo = ctk.CTkComboBox(row, values=["Pending", "Delayed", "Completed"], variable=var, width=120, command=on_status_change)
                combo.grid(row=0, column=2, padx=10, pady=10)

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
                messagebox.showinfo("Success", "Task statuses updated successfully.")
                self.fetch_tasks(self.combo_dept.get())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update tasks:\n{e}")
        finally:
            self.btn_submit_updates.configure(state="normal")

    def show_checklist_dialog(self, goal):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Checklist for {goal.goal_id}")
        dialog.geometry("500x500")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (500 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (500 // 2)
        dialog.geometry(f"+{x}+{y}")

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(scroll, text="Checklist:", font=FONTS["body_bold"], text_color=COLORS["text_main"]).pack(anchor="w", pady=(10, 0))
        chk_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        chk_frame.pack(fill="x", pady=(5, 10))
        
        checkbox_vars = []

        for i, item in enumerate(goal.checklist):
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
            
            var = ctk.BooleanVar(value=is_checked)
            checkbox_vars.append(var)
            
            item_card = ctk.CTkFrame(chk_frame, fg_color=COLORS["input_bg"], corner_radius=6, border_width=1, border_color=COLORS["border"])
            item_card.pack(fill="x", pady=4, ipady=4)
            item_card.grid_columnconfigure(1, weight=1)
            
            lbl = ctk.CTkLabel(item_card, text=text, font=FONTS["body"], text_color=COLORS["text_dim"] if is_checked else COLORS["text_main"], justify="left", wraplength=400)
            
            def on_toggle(idx=i, v=var, g=goal, l=lbl):
                new_state = v.get()
                l.configure(text_color=COLORS["text_dim"] if new_state else COLORS["text_main"])
                if isinstance(g.checklist[idx], dict):
                    g.checklist[idx]["completed"] = new_state
                elif isinstance(g.checklist[idx], str):
                    prefix = "[x]" if new_state else "[ ]"
                    base_text = str(g.checklist[idx])
                    if base_text.startswith("[x]") or base_text.startswith("[ ]"):
                        base_text = base_text[3:].strip()
                    g.checklist[idx] = f"{prefix} {base_text}"
                threading.Thread(target=lambda: self.sheets_client.update_monthly_goal_checklist(g.goal_id, g.checklist), daemon=True).start()
            
            chk = ctk.CTkCheckBox(item_card, text="", variable=var, command=on_toggle, width=24)
            chk.grid(row=0, column=0, padx=(10, 5), pady=8, sticky="n")
            lbl.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="w")

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20, padx=20)
        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, height=38,
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"]).pack(side="right", expand=True)
