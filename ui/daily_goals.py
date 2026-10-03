import customtkinter as ctk
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from config import COLORS, FONTS, ALL_EMPLOYEES
from services.n8n_client import N8nClient

from tkcalendar import DateEntry

class DailyGoalsFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.n8n_client = N8nClient()
        self.pack(fill="both", expand=True, padx=20, pady=20)
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
