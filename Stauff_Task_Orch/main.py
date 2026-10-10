import os
import sys
import logging

# Ensure project root is on path for config import
if getattr(sys, 'frozen', False):
    _project_root = os.path.dirname(sys.executable)
else:
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from config import SUPABASE_URL, SUPABASE_KEY
from data.repository import SupabaseRepository
from ui.main_window import MainWindow
import customtkinter as ctk

# Monkey patch CTkButton to always use cursor="hand2" for hover effect
original_button_init = ctk.CTkButton.__init__
def new_button_init(self, *args, **kwargs):
    kwargs.setdefault('cursor', 'hand2')
    original_button_init(self, *args, **kwargs)
ctk.CTkButton.__init__ = new_button_init

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def fade_in(window, target_alpha=1.0, current=0.0, step=0.08, delay=15):
    try:
        if current < target_alpha:
            current += step
            if current > target_alpha:
                current = target_alpha
            window.attributes("-alpha", current)
            window.after(delay, fade_in, window, target_alpha, current, step, delay)
        else:
            window.attributes("-alpha", target_alpha)
    except Exception:
        pass

def main():
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    # Use live Supabase data
    repository = SupabaseRepository(base_url=SUPABASE_URL, api_key=SUPABASE_KEY)

    app = MainWindow(repository)
    app.attributes("-alpha", 0.0)
    fade_in(app)
    app.mainloop()

if __name__ == "__main__":
    main()
