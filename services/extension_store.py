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
import sys
from datetime import datetime
from typing import List, Dict

import requests

from config import SUPABASE_URL, SUPABASE_KEY

_lock = threading.Lock()

# Cache to avoid hitting Google Sheets on every call
_cache = {
    "data": [],
    "timestamp": 0,
}
_CACHE_TTL_SECONDS = 5  # Refetch at most every 5 seconds
# Local overrides to mask Google Sheets 5-minute publish delay
import os
import json

if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
_OVERRIDES_FILE = os.path.join(_APP_DIR, "extension_overrides.json")

def _load_overrides():
    try:
        if os.path.exists(_OVERRIDES_FILE):
            with open(_OVERRIDES_FILE, "r") as f:
                data = json.load(f)
                # Only keep overrides for 10 minutes max
                now = time.time()
                return {k: v for k, v in data.items() if now - v.get("_ts", 0) < 600}
    except Exception:
        pass
    return {}

def _save_overrides(overrides):
    try:
        with open(_OVERRIDES_FILE, "w") as f:
            json.dump(overrides, f)
    except Exception:
        pass

_local_overrides = _load_overrides()

# ── Read from Google Sheets (published CSV) ──────────────────────────

def _fetch_all_from_sheet() -> List[Dict]:
    """Fetch all extension requests from Supabase REST API."""
    now = time.time()
    if _cache["data"] and (now - _cache["timestamp"]) < _CACHE_TTL_SECONDS:
        return _cache["data"]

    if not SUPABASE_URL or 'your-project' in SUPABASE_URL:
        return _cache["data"]
        
    url = f"{SUPABASE_URL}/rest/v1/extension_requests?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        raw_data = response.json()
        rows = []
        for row in raw_data:
            req_id = str(row.get("request_id", ""))
            if not req_id: continue
            
            row_data = {
                "id": req_id,
                "task_id": row.get("task_id", ""),
                "task_description": row.get("task_description", ""),
                "employee": row.get("employee_name", ""),
                "department": row.get("department", ""),
                "current_deadline": row.get("current_deadline", ""),
                "requested_deadline": row.get("requested_deadline", ""),
                "reason": row.get("reason", ""),
                "status": row.get("status", "Pending"),
                "manager_deadline": row.get("manager_deadline", ""),
                "manager_note": row.get("manager_note", ""),
                "submitted_at": row.get("created_at", ""),
                "decided_at": ""
            }
            
            # Apply local optimistic overrides
            if row_data["status"] == "Pending" and req_id in _local_overrides:
                override = _local_overrides[req_id]
                row_data["status"] = override.get("status", row_data["status"])
                row_data["manager_deadline"] = override.get("manager_deadline", row_data["manager_deadline"])
                row_data["manager_note"] = override.get("manager_note", row_data["manager_note"])
                row_data["decided_at"] = override.get("decided_at", row_data["decided_at"])
            elif row_data["status"] != "Pending":
                _local_overrides[req_id] = {
                    "status": row_data["status"],
                    "manager_deadline": row_data["manager_deadline"],
                    "manager_note": row_data["manager_note"],
                    "decided_at": row_data["decided_at"],
                    "_ts": time.time(),
                }
                _save_overrides(_local_overrides)
                
            rows.append(row_data)
            
        _cache["data"] = rows
        _cache["timestamp"] = now
        return rows
    except Exception as e:
        print(f"Error fetching extension requests from Supabase: {e}")
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
        
        # Save optimistic local override
        _local_overrides[request_id] = {
            "status": decision,
            "manager_deadline": manager_deadline,
            "manager_note": manager_note,
            "decided_at": payload["decided_at"],
            "_ts": time.time(),
        }
        _save_overrides(_local_overrides)
        
        _invalidate_cache()
        return True
    except Exception as e:
        print(f"Failed to submit extension decision via n8n: {e}")
        return False
