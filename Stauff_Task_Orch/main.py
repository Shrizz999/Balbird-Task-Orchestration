import os
import logging
from data.repository import GoogleSheetRepository
from ui.main_window import MainWindow
import customtkinter as ctk

# Published Google Sheet base URL
GSHEET_BASE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTHrHDX22vdQV7YQKrDOenwKBBenyG98ERPGBysBRRW-iKEuKBAryRb6hOQ_-zNuG2hq0Vd-KlBVN2o/pub"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    # Use live Google Sheet data
    repository = GoogleSheetRepository(base_url=GSHEET_BASE_URL)

    app = MainWindow(repository)
    app.mainloop()


if __name__ == "__main__":
    main()
