import customtkinter as ctk
from config import COLORS, FONTS
from ui.daily_goals import DailyGoalsFrame
from ui.department_goals import DepartmentGoalsFrame
from ui.tasks_updates import TasksUpdatesFrame
from ui.monthly_tasks_updates import MonthlyTasksUpdatesFrame

class StauffApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Stauff Task Orchestrator")
        self.geometry("1100x800")
        self.configure(fg_color=COLORS["bg"])
        
        # Grid layout: Sidebar on left (col 0), Main on right (col 1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.frames = {}
        self.active_btn = None
        self.nav_buttons = []

        self.setup_sidebar()
        self.setup_main_area()
        self.show_frame("DailyGoals")

    def setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, fg_color=COLORS["sidebar_bg"], corner_radius=0, width=250)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        lbl_logo = ctk.CTkLabel(self.sidebar_frame, text="Stauff TO", font=FONTS["header"], text_color=COLORS["sidebar_text"])
        lbl_logo.pack(pady=(30, 40), padx=20, anchor="w")

        nav_items = [
            ("Daily Goals", "DailyGoals"),
            ("Department Goals", "DepartmentGoals"),
            ("Meeting Updates", "TasksUpdates"),
            ("Monthly Task Updater", "MonthlyTasksUpdates")
        ]

        for text, frame_name in nav_items:
            btn = ctk.CTkButton(
                self.sidebar_frame, 
                text=text, 
                font=FONTS["body_bold"], 
                fg_color="transparent", 
                text_color=COLORS["sidebar_text"], 
                hover_color=COLORS["sidebar_hover"], 
                anchor="w",
                corner_radius=8,
                height=40,
                command=lambda f=frame_name, t=text: self.on_nav_click(f, t)
            )
            btn.pack(pady=5, padx=15, fill="x")
            self.nav_buttons.append((text, btn))

    def setup_main_area(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew")
        
        # Initialize all frames
        self.frames["DailyGoals"] = DailyGoalsFrame(self.main_container)
        self.frames["DepartmentGoals"] = DepartmentGoalsFrame(self.main_container)
        self.frames["TasksUpdates"] = TasksUpdatesFrame(self.main_container)
        self.frames["MonthlyTasksUpdates"] = MonthlyTasksUpdatesFrame(self.main_container)
        
        # Hide all initially
        for frame in self.frames.values():
            frame.pack_forget()

    def on_nav_click(self, frame_name: str, btn_text: str):
        # Update button colors
        for text, btn in self.nav_buttons:
            if text == btn_text:
                btn.configure(fg_color=COLORS["sidebar_hover"], text_color=COLORS["sidebar_text_active"])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["sidebar_text"])
                
        self.show_frame(frame_name)

    def show_frame(self, frame_name: str):
        for frame in self.frames.values():
            frame.pack_forget()
            
        frame = self.frames.get(frame_name)
        if frame:
            if hasattr(frame, "load_data"):
                frame.load_data() # Refresh data if applicable
            frame.pack(fill="both", expand=True)
            
        # Select first button if none active (init)
        if frame_name == "DailyGoals":
            for text, btn in self.nav_buttons:
                if text == "Daily Goals":
                    btn.configure(fg_color=COLORS["sidebar_hover"], text_color=COLORS["sidebar_text_active"])

if __name__ == "__main__":
    app = StauffApp()
    app.mainloop()