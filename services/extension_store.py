"""
Shared store for deadline extension requests.

Both the employee app (task_updater_app.py) and the manager dashboard
(Stauff_Task_Orch/main.py) communicate via Google Sheets (read) and
n8n webhooks (write) so that extension requests work across devices.
"""

import csv
import io
import time
import uuid
import threading
from datetime import datetime
from typing import List, Dict

import requests

from config import SHEET_BASE_URL, SHEET_GIDS

_lock = threading.Lock()

# Cache to avoid hitting Google Sheets on every call
_cache = {
    "data": [],
    "timestamp": 0,
}
_CACHE_TTL_SECONDS = 15  # Refetch at most every 15 seconds


# ── Read from Google Sheets (published CSV) ──────────────────────────

def _fetch_all_from_sheet() -> List[Dict]:
    """Fetch all extension requests from the published Google Sheet CSV."""
    gid = SHEET_GIDS.get("Extensions")
    if not gid:
        return []

    now = time.time()
    if _cache["data"] and (now - _cache["timestamp"]) < _CACHE_TTL_SECONDS:
        return _cache["data"]

    url = f"{SHEET_BASE_URL}{gid}&_={int(now)}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        f = io.StringIO(response.text)
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            if not row.get("ID"):
                continue
            rows.append({
                "id": row.get("ID", ""),
                "task_id": row.get("Task ID", ""),
                "task_description": row.get("Task Description", ""),
                "employee": row.get("Employee", ""),
                "department": row.get("Department", ""),
                "current_deadline": row.get("Current Deadline", ""),
                "requested_deadline": row.get("Requested Deadline", ""),
                "reason": row.get("Reason", ""),
                "status": row.get("Status", "Pending"),
                "manager_deadline": row.get("Manager Deadline", ""),
                "manager_note": row.get("Manager Note", ""),
                "submitted_at": row.get("Submitted At", ""),
                "decided_at": row.get("Decided At", ""),
            })
        _cache["data"] = rows
        _cache["timestamp"] = now
        return rows
    except Exception as e:
        print(f"Error fetching extension requests from sheet: {e}")
        return _cache["data"]  # Return stale cache on error


def _invalidate_cache():
    """Force the next read to refetch from Google Sheets."""
    _cache["timestamp"] = 0


# ── Write via n8n webhook ────────────────────────────────────────────

def _get_n8n_client():
    """Lazy import to avoid circular imports."""
    from services.n8n_client import N8nClient
    return N8nClient()


# ── Employee-side helpers ────────────────────────────────────────────

def submit_extension_request(
    task_id: str,
    task_description: str,
    employee_name: str,
    current_deadline: str,
    requested_deadline: str,
    reason: str,
    department: str = "",
) -> str:
    """Create a new extension request via n8n webhook. Returns the request ID."""
    req_id = str(uuid.uuid4())[:8]
    payload = {
        "action": "submit",
        "id": req_id,
        "task_id": task_id,
        "task_description": task_description,
        "employee": employee_name,
        "department": department,
        "current_deadline": current_deadline,
        "requested_deadline": requested_deadline,
        "reason": reason,
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    try:
        n8n = _get_n8n_client()
        n8n.submit_extension_request(payload)
    except Exception as e:
        print(f"Failed to submit extension request via n8n: {e}")
        raise

    _invalidate_cache()
    return req_id


def get_requests_for_employee(employee_name: str) -> List[Dict]:
    """Return all extension requests submitted by a given employee."""
    store = _fetch_all_from_sheet()
    return [r for r in store if r["employee"] == employee_name]


def get_decided_requests_for_employee(employee_name: str) -> List[Dict]:
    """Return requests that the manager has already decided on."""
    return [r for r in get_requests_for_employee(employee_name) if r["status"] != "Pending"]


def get_pending_requests_for_employee(employee_name: str) -> List[Dict]:
    """Return requests still awaiting a manager decision."""
    return [r for r in get_requests_for_employee(employee_name) if r["status"] == "Pending"]


# ── Manager-side helpers ─────────────────────────────────────────────

def get_all_pending_requests() -> List[Dict]:
    """Return all extension requests that haven't been decided yet."""
    store = _fetch_all_from_sheet()
    return [r for r in store if r["status"] == "Pending"]


def get_all_requests() -> List[Dict]:
    """Return every extension request (all statuses)."""
    return _fetch_all_from_sheet()


def decide_request(
    request_id: str,
    decision: str,             # "Approved" or "Rejected"
    manager_deadline: str = "",
    manager_note: str = "",
) -> bool:
    """
    Record the manager's decision on an extension request via n8n webhook.
    If manager_deadline is empty and decision is Approved, the
    employee's requested deadline is used.
    Returns True on success.
    """
    payload = {
        "action": "decide",
        "id": request_id,
        "status": decision,
        "manager_deadline": manager_deadline,
        "manager_note": manager_note,
        "decided_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    try:
        n8n = _get_n8n_client()
        n8n.submit_extension_decision(payload)
        _invalidate_cache()
        return True
    except Exception as e:
        print(f"Failed to submit extension decision via n8n: {e}")
        return False
