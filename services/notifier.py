"""
Native Windows Action Center Toast Notification Service for Balbird TO.

Provides:
- Native Windows 10/11 Toast Notifications with Action Center persistence and audio chimes.
- In-process delivery using `winotify`, with automated fallback to PowerShell WinRT.
- Thread-safe, non-blocking execution (always dispatches in background daemon threads).
- Deduplication cache with TTL to prevent alert spam.
- Windows Startup integration (adds/removes shortcut in Windows Startup directory).
"""

import os
import sys
import time
import base64
import logging
import threading
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

# Cache for deduplicating notifications: {event_key: timestamp}
_notified_events = {}
_CACHE_LOCK = threading.Lock()
_DEFAULT_DEDUP_WINDOW_SECONDS = 1800  # 30 minutes


def _resolve_icon(icon_name: str) -> Optional[str]:
    """Finds absolute path to icon file in project or executable bundle."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    candidates = [
        os.path.join(base_dir, icon_name),
        os.path.join(os.getcwd(), icon_name),
    ]
    if hasattr(sys, '_MEIPASS'):
        candidates.insert(0, os.path.join(sys._MEIPASS, icon_name))

    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return None


def _clean_old_cache(now: float):
    """Removes expired entries from deduplication cache."""
    keys_to_del = [k for k, t in _notified_events.items() if now - t > _DEFAULT_DEDUP_WINDOW_SECONDS]
    for k in keys_to_del:
        del _notified_events[k]


def is_already_notified(event_key: str, dedup_window: float = _DEFAULT_DEDUP_WINDOW_SECONDS) -> bool:
    """Checks whether an event has been notified recently."""
    now = time.time()
    with _CACHE_LOCK:
        _clean_old_cache(now)
        last_time = _notified_events.get(event_key)
        if last_time and (now - last_time < dedup_window):
            return True
        _notified_events[event_key] = now
        return False


def send_notification(
    title: str,
    message: str,
    app_id: str = "Balbird TO",
    icon_path: Optional[str] = None,
    sound: bool = True,
    dedup_key: Optional[str] = None,
    dedup_window: float = _DEFAULT_DEDUP_WINDOW_SECONDS
):
    """
    Sends a native Windows Toast notification asynchronously without blocking the UI.
    If `dedup_key` is supplied, suppresses repeats within `dedup_window`.
    """
    if dedup_key and is_already_notified(dedup_key, dedup_window):
        return

    def _worker():
        try:
            _show_toast_winotify(title, message, app_id, icon_path, sound)
        except Exception as e:
            # Fallback to PowerShell WinRT
            try:
                _show_toast_powershell(title, message, app_id, icon_path)
            except Exception as e2:
                logger.debug(f"[notifier] Failed to send toast: {e}; fallback: {e2}")

    threading.Thread(target=_worker, daemon=True, name="ToastNotifierThread").start()


def _show_toast_winotify(title: str, message: str, app_id: str, icon_path: Optional[str], sound: bool):
    """Primary in-process Windows notification via winotify."""
    try:
        from winotify import Notification, audio
    except ImportError:
        raise RuntimeError("winotify not installed, using fallback")

    toast = Notification(
        app_id=app_id,
        title=title,
        msg=message,
        icon=icon_path if (icon_path and os.path.exists(icon_path)) else ""
    )
    if sound:
        toast.set_audio(audio.Default, loop=False)
    else:
        toast.set_audio(audio.Silent, loop=False)

    toast.show()


def _show_toast_powershell(title: str, message: str, app_id: str, icon_path: Optional[str] = None):
    """Fallback Windows WinRT notification using encoded PowerShell."""
    safe_title = title.replace('"', '`"').replace('$', '`$')
    safe_msg = message.replace('"', '`"').replace('$', '`$')

    icon_xml = ""
    if icon_path and os.path.exists(icon_path):
        icon_uri = icon_path.replace("\\", "/")
        icon_xml = f'<image placement="appLogoOverride" src="file:///{icon_uri}" />'

    ps_code = f"""
$ProgressPreference = 'SilentlyContinue'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlCommands, ContentType = WindowsRuntime] | Out-Null

$xml = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            {icon_xml}
            <text>{safe_title}</text>
            <text>{safe_msg}</text>
        </binding>
    </visual>
</toast>
"@

$toastXml = New-Object Windows.Data.Xml.Dom.XmlDocument
$toastXml.LoadXml($xml)
$toast = New-Object Windows.UI.Notifications.ToastNotification $toastXml
$app = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show($toast)
"""
    encoded = base64.b64encode(ps_code.encode("utf-16le")).decode("ascii")
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    )


# ═════════════════════════════════════════════════════════════════════
# Specific Event Handlers: Employee Portal
# ═════════════════════════════════════════════════════════════════════

def notify_employee_new_task(task, icon_path: Optional[str] = None):
    """Alerts employee when a new task is assigned to them."""
    if not icon_path:
        icon_path = _resolve_icon("user.ico")
    t_id = str(getattr(task, "task_id", "") or "")
    short_id = t_id[-4:] if len(t_id) >= 4 else t_id
    prio = getattr(task, "priority", "Normal")
    desc = getattr(task, "description", "") or getattr(task, "task", "") or "New task assigned"
    deadline = getattr(task, "deadline", "")
    dl_text = f" • Due: {deadline}" if deadline else ""

    send_notification(
        title="Balbird TO • New Task Assigned",
        message=f"[#{short_id}] ({prio}) {desc}{dl_text}",
        app_id="Balbird TO - Employee Portal",
        icon_path=icon_path,
        dedup_key=f"emp_new_task_{t_id}"
    )


def notify_employee_extension_resolved(task_id: str, status: str, new_deadline: str = "", icon_path: Optional[str] = None):
    """Alerts employee when manager approves or rejects their extension request."""
    if not icon_path:
        icon_path = _resolve_icon("user.ico")
    short_id = str(task_id)[-4:] if len(str(task_id)) >= 4 else str(task_id)

    if status.lower() == "approved":
        title = "Balbird TO • Extension Approved ✓"
        msg = f"Your extension request for [#{short_id}] has been APPROVED. New deadline: {new_deadline}."
    else:
        title = "Balbird TO • Extension Declined"
        msg = f"Your extension request for [#{short_id}] was not approved."

    send_notification(
        title=title,
        message=msg,
        app_id="Balbird TO - Employee Portal",
        icon_path=icon_path,
        dedup_key=f"emp_ext_{task_id}_{status.lower()}"
    )


def notify_employee_task_overdue(task, overdue_days: int, icon_path: Optional[str] = None):
    """Alerts employee when their task has breached deadline."""
    if not icon_path:
        icon_path = _resolve_icon("user.ico")
    t_id = str(getattr(task, "task_id", "") or "")
    short_id = t_id[-4:] if len(t_id) >= 4 else t_id
    desc = getattr(task, "description", "") or "Task"
    
    send_notification(
        title="Balbird TO • Task Overdue / Action Required",
        message=f"[#{short_id}] '{desc}' is overdue by {overdue_days}d. Please complete it or request an extension.",
        app_id="Balbird TO - Employee Portal",
        icon_path=icon_path,
        dedup_key=f"emp_overdue_{t_id}",
        dedup_window=43200  # Notify once every 12 hours
    )


# ═════════════════════════════════════════════════════════════════════
# Specific Event Handlers: HOD / Manager (Admin Dashboard)
# ═════════════════════════════════════════════════════════════════════

def notify_admin_task_completed(task, icon_path: Optional[str] = None):
    """Alerts HOD/manager when an employee completes a task."""
    if not icon_path:
        icon_path = _resolve_icon("admin.ico")
    t_id = str(getattr(task, "task_id", "") or getattr(task, "Task_ID", "") or "")
    short_id = t_id[-4:] if len(t_id) >= 4 else t_id
    assigned_to = getattr(task, "assigned_to", "") or getattr(task, "Assigned_To", "Employee")
    desc = getattr(task, "task_description", "") or getattr(task, "description", "") or "Task"

    send_notification(
        title="Balbird TO • Task Completed ✓",
        message=f"{assigned_to} completed [#{short_id}]: {desc}",
        app_id="Balbird TO - Admin Dashboard",
        icon_path=icon_path,
        dedup_key=f"admin_completed_{t_id}"
    )


def notify_admin_extension_requested(req, icon_path: Optional[str] = None):
    """Alerts HOD/manager when an employee submits a new extension request."""
    if not icon_path:
        icon_path = _resolve_icon("admin.ico")
    req_id = str(req.get("id") or req.get("task_id", ""))
    t_id = str(req.get("task_id", ""))
    short_id = t_id[-4:] if len(t_id) >= 4 else t_id
    emp = req.get("employee_name", "Employee")
    req_dl = req.get("requested_deadline", "")
    reason = req.get("reason", "No reason provided")

    send_notification(
        title="Balbird TO • New Extension Request ⏰",
        message=f"{emp} requested extension for [#{short_id}] to {req_dl}. Reason: {reason}",
        app_id="Balbird TO - Admin Dashboard",
        icon_path=icon_path,
        dedup_key=f"admin_ext_req_{req_id}"
    )


def notify_admin_task_escalation(task, overdue_days: int, icon_path: Optional[str] = None):
    """Alerts HOD/manager when a high or urgent task breaches deadline."""
    if not icon_path:
        icon_path = _resolve_icon("admin.ico")
    t_id = str(getattr(task, "task_id", "") or getattr(task, "Task_ID", "") or "")
    short_id = t_id[-4:] if len(t_id) >= 4 else t_id
    assigned_to = getattr(task, "assigned_to", "") or getattr(task, "Assigned_To", "Employee")
    prio = getattr(task, "priority", "") or getattr(task, "Priority", "High")
    desc = getattr(task, "task_description", "") or getattr(task, "description", "") or "Task"

    send_notification(
        title=f"Balbird TO • Escalation: {prio.upper()} Task Overdue ⚠",
        message=f"[#{short_id}] ({assigned_to}) is overdue by {overdue_days}d: {desc}",
        app_id="Balbird TO - Admin Dashboard",
        icon_path=icon_path,
        dedup_key=f"admin_escalate_{t_id}",
        dedup_window=43200  # Once every 12 hours
    )


# ═════════════════════════════════════════════════════════════════════
# Windows Startup Integration Helpers
# ═════════════════════════════════════════════════════════════════════

def get_windows_startup_dir() -> str:
    """Returns the Windows user Startup directory path."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = os.path.expanduser(r"~\AppData\Roaming")
    return os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")


def enable_windows_startup(app_name: str, target_path: Optional[str] = None) -> bool:
    """
    Registers the application to launch automatically on Windows user login
    by placing a standard startup script in the Windows Startup folder.
    """
    try:
        startup_dir = get_windows_startup_dir()
        os.makedirs(startup_dir, exist_ok=True)
        bat_file = os.path.join(startup_dir, f"{app_name}.bat")

        if not target_path:
            if getattr(sys, "frozen", False):
                target_path = sys.executable
            else:
                target_path = os.path.abspath(sys.argv[0])

        target_dir = os.path.dirname(os.path.abspath(target_path))
        target_name = os.path.basename(target_path)

        # Batch launcher that navigates to directory and launches target
        if target_path.endswith(".py"):
            py_exe = sys.executable
            content = f'@echo off\ncd /d "{target_dir}"\nstart "" "{py_exe}" "{target_name}"\n'
        else:
            content = f'@echo off\ncd /d "{target_dir}"\nstart "" "{target_name}"\n'

        with open(bat_file, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"[notifier] Failed to enable startup for {app_name}: {e}")
        return False


def disable_windows_startup(app_name: str) -> bool:
    """Removes the application from the Windows user Startup folder."""
    try:
        startup_dir = get_windows_startup_dir()
        bat_file = os.path.join(startup_dir, f"{app_name}.bat")
        if os.path.exists(bat_file):
            os.remove(bat_file)
        return True
    except Exception as e:
        logger.error(f"[notifier] Failed to disable startup for {app_name}: {e}")
        return False


def is_windows_startup_enabled(app_name: str) -> bool:
    """Checks whether the application is registered in Windows Startup."""
    startup_dir = get_windows_startup_dir()
    bat_file = os.path.join(startup_dir, f"{app_name}.bat")
    return os.path.exists(bat_file)
