import customtkinter as ctk
import requests
from config import SUPABASE_URL, SUPABASE_KEY, DEPARTMENTS
from .components import CARD_BG, BORDER_COLOR, TEXT_COLOR, TEXT_MUTED, ACCENT_COLOR

class AddEmployeeView(ctk.CTkFrame):
    def __init__(self, master, repository):
        super().__init__(master, fg_color="transparent")
        self.repository = repository

        self.grid_columnconfigure(0, weight=1)
        
        lbl_title = ctk.CTkLabel(self, text="Add New Employee", font=("Inter", 24, "bold"), text_color=TEXT_COLOR)
        lbl_title.grid(row=0, column=0, padx=40, pady=(40, 10), sticky="w")
        
        lbl_desc = ctk.CTkLabel(self, text="Register a new employee. This will automatically update department lists and analytics.",
                                font=("Inter", 14), text_color=TEXT_MUTED)
        lbl_desc.grid(row=1, column=0, padx=40, pady=(0, 30), sticky="w")

        form_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        form_frame.grid(row=2, column=0, padx=40, pady=10, sticky="nwe")
        form_frame.grid_columnconfigure(1, weight=1)

        # Name
        ctk.CTkLabel(form_frame, text="Name:", font=("Inter", 13, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.entry_name = ctk.CTkEntry(form_frame, font=("Inter", 13), placeholder_text="e.g. John Doe", width=300)
        self.entry_name.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="w")

        # Department
        ctk.CTkLabel(form_frame, text="Department:", font=("Inter", 13, "bold"), text_color=TEXT_COLOR).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        
        dept_options = list(DEPARTMENTS.keys())
        if not dept_options:
            dept_options = ["SO department", "PO department", "Sales Department", "Logistics Department"]
            
        self.combo_dept = ctk.CTkComboBox(form_frame, values=dept_options, font=("Inter", 13), width=300)
        self.combo_dept.grid(row=1, column=1, padx=20, pady=10, sticky="w")
        
        # Phone
        ctk.CTkLabel(form_frame, text="Phone Number:", font=("Inter", 13, "bold"), text_color=TEXT_COLOR).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.entry_phone = ctk.CTkEntry(form_frame, font=("Inter", 13), placeholder_text="Optional", width=300)
        self.entry_phone.grid(row=2, column=1, padx=20, pady=10, sticky="w")
        
        # Email
        ctk.CTkLabel(form_frame, text="Email Address:", font=("Inter", 13, "bold"), text_color=TEXT_COLOR).grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.entry_email = ctk.CTkEntry(form_frame, font=("Inter", 13), placeholder_text="Optional", width=300)
        self.entry_email.grid(row=3, column=1, padx=20, pady=10, sticky="w")
        
        # Submit
        self.btn_submit = ctk.CTkButton(form_frame, text="Register Employee", font=("Inter", 14, "bold"),
                                        fg_color=ACCENT_COLOR, text_color="white", command=self.on_submit)
        self.btn_submit.grid(row=4, column=0, columnspan=2, padx=20, pady=(20, 20), sticky="w")

        self.lbl_status = ctk.CTkLabel(form_frame, text="", font=("Inter", 12))
        self.lbl_status.grid(row=5, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="w")

    def on_submit(self):
        name = self.entry_name.get().strip()
        dept = self.combo_dept.get().strip()
        phone = self.entry_phone.get().strip()
        email = self.entry_email.get().strip()
        
        if not name or not dept:
            self.lbl_status.configure(text="Name and Department are required.", text_color="red")
            return
            
        self.btn_submit.configure(state="disabled", text="Registering...")
        
        def do_request():
            url = f"{SUPABASE_URL}/rest/v1/employees"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            payload = {
                "name": name,
                "department": dept,
                "phone_number": phone if phone else None,
                "email": email if email else None
            }
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=10)
                if resp.status_code in (200, 201):
                    # update local config
                    if dept not in DEPARTMENTS:
                        DEPARTMENTS[dept] = []
                    if name not in DEPARTMENTS[dept]:
                        DEPARTMENTS[dept].append(name)
                        
                    import config
                    config.ALL_DEPARTMENTS.clear()
                    config.ALL_DEPARTMENTS.extend(list(config.DEPARTMENTS.keys()))
                    config.ALL_EMPLOYEES.clear()
                    config.ALL_EMPLOYEES.extend([emp for emps in config.DEPARTMENTS.values() for emp in emps])
                        
                    self.after(0, lambda: self.lbl_status.configure(text="Employee added successfully!", text_color="green"))
                    
                    if hasattr(self.winfo_toplevel(), "update_dropdowns"):
                        self.after(0, self.winfo_toplevel().update_dropdowns)
                    self.after(0, lambda: self.entry_name.delete(0, 'end'))
                    self.after(0, lambda: self.entry_phone.delete(0, 'end'))
                    self.after(0, lambda: self.entry_email.delete(0, 'end'))
                    
                    if hasattr(self.repository, "refresh_async"):
                        self.repository.refresh_async()
                else:
                    self.after(0, lambda: self.lbl_status.configure(text=f"Failed: {resp.text}", text_color="red"))
            except Exception as e:
                self.after(0, lambda: self.lbl_status.configure(text=f"Error: {e}", text_color="red"))
            finally:
                self.after(0, lambda: self.btn_submit.configure(state="normal", text="Register Employee"))
                
        import threading
        threading.Thread(target=do_request, daemon=True).start()
