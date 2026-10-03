"""
Shared store for deadline extension requests.

Both the employee app (task_updater_app.py) and the manager dashboard
(Stauff_Task_Orch/main.py) read and write to a single JSON file so
that extension requests flow from employee → manager and decisions
flow back manager → employee.
"""

import json
import os
import sys
import uuid
import threading
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Store the file next to the exe (frozen) or next to this module's parent (dev)
if getattr(sys, 'frozen', False):
    _STORE_PATH = Path(sys.executable).resolve().parent / "extension_requests.json"
else:
    _STORE_PATH = Path(__file__).resolve().parent.parent / "extension_requests.json"
_lock = threading.Lock()


def _read_store() -> List[Dict]:
    """Read all extension requests from disk."""
    if not _STORE_PATH.exists():
        return []
    try:
        with open(_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _write_store(data: List[Dict]):
    """Write all extension requests to disk."""
    with open(_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Employee-side helpers ────────────────────────────────────────────

def submit_extension_request(
    task_id: str,
    task_description: str,
    employee_name: str,
    current_deadline: str,
    requested_deadline: str,
    reason: str,
) -> str:
    """Create a new extension request. Returns the request ID."""
    with _lock:
        store = _read_store()
        req_id = str(uuid.uuid4())[:8]
        store.append({
            "id": req_id,
            "task_id": task_id,
            "task_description": task_description,
            "employee": employee_name,
            "current_deadline": current_deadline,
            "requested_deadline": requested_deadline,
            "reason": reason,
            "status": "Pending",           # Pending | Approved | Rejected
            "manager_deadline": "",         # Manager may override with a custom date
            "manager_note": "",
            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "decided_at": "",
        })
        _write_store(store)
    return req_id


def get_requests_for_employee(employee_name: str) -> List[Dict]:
    """Return all extension requests submitted by a given employee."""
    store = _read_store()
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
    store = _read_store()
    return [r for r in store if r["status"] == "Pending"]


def get_all_requests() -> List[Dict]:
    """Return every extension request (all statuses)."""
    return _read_store()


def decide_request(
    request_id: str,
    decision: str,             # "Approved" or "Rejected"
    manager_deadline: str = "",
    manager_note: str = "",
) -> bool:
    """
    Record the manager's decision on an extension request.
    If manager_deadline is empty and decision is Approved, the
    employee's requested deadline is used.
    Returns True on success.
    """
    with _lock:
        store = _read_store()
        for req in store:
            if req["id"] == request_id:
                req["status"] = decision
                req["manager_deadline"] = manager_deadline
                req["manager_note"] = manager_note
                req["decided_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                _write_store(store)
                return True
    return False
