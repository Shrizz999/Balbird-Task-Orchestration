import os
import sys
import logging
import threading
import traceback
from datetime import datetime

# Ensure project root and package directory are on path
_this_dir = os.path.abspath(os.path.dirname(__file__))
if getattr(sys, 'frozen', False):
    _project_root = os.path.dirname(sys.executable)
else:
    _project_root = os.path.abspath(os.path.join(_this_dir, ".."))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ── Crash-Proof Safety Net ───────────────────────────────────────────────
def _setup_crash_proof_environment():
    """Catches unhandled errors in main and worker threads, logs to crash_log.txt without crashing."""
    log_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else _project_root
    crash_log_file = os.path.join(log_dir, "crash_log.txt")

    def global_excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.critical(f"Unhandled exception prevented:\n{err_msg}")
        try:
            with open(crash_log_file, "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] UNHANDLED ERROR:\n{err_msg}\n")
        except Exception:
            pass

    sys.excepthook = global_excepthook

    if hasattr(threading, 'excepthook'):
        def thread_excepthook(args):
            err_msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
            logging.error(f"Thread error in {args.thread.name} prevented:\n{err_msg}")
            try:
                with open(crash_log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] THREAD ERROR ({args.thread.name}):\n{err_msg}\n")
            except Exception:
                pass
        threading.excepthook = thread_excepthook

_setup_crash_proof_environment()

def resolve_resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(p):
            return p
    if getattr(sys, 'frozen', False):
        p = os.path.join(os.path.dirname(sys.executable), filename)
        if os.path.exists(p):
            return p
    candidates = [
        os.path.join(_project_root, filename),
        os.path.join(os.path.dirname(__file__), filename),
        os.path.join(os.getcwd(), filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return filename

from config import SUPABASE_URL, SUPABASE_KEY, SHOW_MEETING_TRANSCRIPTS, SHOW_DAILY_UPDATES
# UI Feature Flags: Controls Meeting Transcript & Daily Updates visibility in Admin Dashboard.
# To bring them back, set SHOW_MEETING_TRANSCRIPTS = True and SHOW_DAILY_UPDATES = True in config.py
# (or override here: config.SHOW_MEETING_TRANSCRIPTS = True; config.SHOW_DAILY_UPDATES = True)
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
    try:
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        # Use live Supabase data with fallback resilience
        try:
            repository = SupabaseRepository(base_url=SUPABASE_URL, api_key=SUPABASE_KEY)
        except Exception as e:
            logging.error(f"Error initializing SupabaseRepository: {e}")
            from data.repository import MockRepository
            repository = MockRepository()

        app = MainWindow(repository)
        app.title("Balbird TO")
        ico_path = resolve_resource_path("admin.ico")
        if os.path.exists(ico_path):
            try:
                app.iconbitmap(ico_path)
            except Exception:
                pass
        app.attributes("-alpha", 0.0)
        fade_in(app)
        app.mainloop()
    except Exception as e:
        err = traceback.format_exc()
        logging.critical(f"Fatal error in main():\n{err}")
        try:
            log_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else _project_root
            with open(os.path.join(log_dir, "crash_log.txt"), "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FATAL APP ERROR:\n{err}\n")
        except Exception:
            pass

if __name__ == "__main__":
    main()
