import customtkinter as ctk
from data.repository import DataRepository, GoogleSheetRepository, TEAM_STRUCTURE
from .dashboard import DashboardView
from .tasks import TasksView
from .goals import GoalsView
from .updates import UpdatesView
from .people import PeopleView
from .analytics import AnalyticsView
from .task_assignment import TaskAssignmentView
from .extension_requests import ExtensionRequestsView
from .components import BG_COLOR, CARD_BG, BORDER_COLOR, TEXT_COLOR, TEXT_MUTED, ACCENT_COLOR

REFRESH_INTERVAL_MS = 120_000  # Auto-refresh every 2 minutes


class MainWindow(ctk.CTk):
    def __init__(self, repository: DataRepository):
        super().__init__()

        self.repository = repository

        self.title("Task Orchestration Dashboard")
        self.geometry("1280x850")
        self.configure(fg_color=BG_COLOR)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()

        # Default view
        self.show_view("Dashboard")

        # Start auto-refresh if live
        if isinstance(self.repository, GoogleSheetRepository):
            self._schedule_auto_refresh()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=CARD_BG, border_width=1,
                                    border_color=BORDER_COLOR, corner_radius=0, width=220)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(20, weight=1)

        lbl_logo = ctk.CTkLabel(self.sidebar, text="STAUFF ORCH",
                                font=("Inter", 18, "bold"), text_color=TEXT_COLOR)
        lbl_logo.grid(row=0, column=0, padx=20, pady=(25, 5), sticky="w")

        self.lbl_live = ctk.CTkLabel(self.sidebar, text="", font=("Inter", 9), text_color=ACCENT_COLOR)
        self.lbl_live.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        if isinstance(self.repository, GoogleSheetRepository):
            self.lbl_live.configure(text="● LIVE — Google Sheets")

        self.current_dept = ctk.StringVar(value="All Departments")
        dept_options = ["All Departments"] + list(TEAM_STRUCTURE.keys())
        
        self.combo_dept = ctk.CTkComboBox(
            self.sidebar, 
            values=dept_options, 
            variable=self.current_dept,
            command=self._on_dept_changed,
            fg_color=BG_COLOR,
            border_color=BORDER_COLOR,
            button_color=ACCENT_COLOR,
            button_hover_color="#0284c7",
        )
        self.combo_dept.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="ew")

        # Navigation
        nav_items = [
            ("Overview", [("Dashboard", DashboardView)]),
            ("Work Management", [
                ("All Tasks", TasksView),
                ("Goals", GoalsView),
                ("Daily Updates", UpdatesView)
            ]),
            ("People", [
                ("Team Profiles", PeopleView),
                ("Analytics", AnalyticsView)
            ]),
            ("Task Assignment", [
                ("Task Assignment", TaskAssignmentView)
            ]),
            ("Approvals", [
                ("Extension Requests", ExtensionRequestsView)
            ])
        ]

        self.nav_buttons = {}
        self.views = {}

        row_idx = 3
        for section, items in nav_items:
            lbl_section = ctk.CTkLabel(self.sidebar, text=section.upper(),
                                       font=("Inter", 10, "bold"), text_color=TEXT_MUTED)
            lbl_section.grid(row=row_idx, column=0, padx=20, pady=(18, 4), sticky="w")
            row_idx += 1

            for item_name, view_class in items:
                btn = ctk.CTkButton(self.sidebar, text=item_name, fg_color="transparent",
                                    text_color=TEXT_COLOR, hover_color=BG_COLOR,
                                    anchor="w", font=("Inter", 13),
                                    command=lambda name=item_name: self.show_view(name))
                btn.grid(row=row_idx, column=0, padx=10, pady=2, sticky="ew")
                self.nav_buttons[item_name] = btn

                view_instance = view_class(self, self.repository)
                self.views[item_name] = view_instance
                row_idx += 1

        # Refresh button at bottom
        self.btn_refresh = ctk.CTkButton(
            self.sidebar, text="↻ Refresh Data", fg_color=ACCENT_COLOR,
            hover_color="#0284c7", text_color="white", font=("Inter", 12, "bold"),
            command=self._manual_refresh
        )
        self.btn_refresh.grid(row=21, column=0, padx=15, pady=(10, 15), sticky="ew")

    def _on_dept_changed(self, choice):
        self._apply_refresh()

    def show_view(self, name: str):
        for btn_name, btn in self.nav_buttons.items():
            btn.configure(fg_color=BG_COLOR if btn_name == name else "transparent")

        for view in self.views.values():
            view.grid_forget()

        view = self.views[name]
        view.grid(row=0, column=1, sticky="nsew")

    def _manual_refresh(self):
        self.btn_refresh.configure(text="Refreshing...", state="disabled")
        if isinstance(self.repository, GoogleSheetRepository):
            self.repository.on_refresh_done = self._on_refresh_complete
            self.repository.refresh_async()
        else:
            self.repository.refresh()
            self._on_refresh_complete()

    def _on_refresh_complete(self):
        # Schedule UI update on main thread
        self.after(0, self._apply_refresh)

    def _apply_refresh(self):
        for view in self.views.values():
            if hasattr(view, 'refresh_data'):
                view.refresh_data()
        self.btn_refresh.configure(text="↻ Refresh Data", state="normal")

    def _schedule_auto_refresh(self):
        def _tick():
            if isinstance(self.repository, GoogleSheetRepository):
                self.repository.on_refresh_done = self._on_refresh_complete
                self.repository.refresh_async()
            self.after(REFRESH_INTERVAL_MS, _tick)
        self.after(REFRESH_INTERVAL_MS, _tick)
