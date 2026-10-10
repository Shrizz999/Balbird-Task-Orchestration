"""
Cloud sync layer for instant cross-app communication using MongoDB.

Google Sheets' published CSV endpoint has a ~5 minute CDN cache delay.
This module provides a shared MongoDB-based cache so that the
Admin Dashboard and Task Updater can see each other's changes immediately
across different computers without waiting for the Google Sheets CDN to refresh.

Overrides auto-expire after 10 minutes, by which time Google Sheets
will have propagated the write.
"""

import time
import threading
from typing import Dict, List, Optional
import pymongo
import logging

logger = logging.getLogger(__name__)

MONGO_URI = "mongodb+srv://stauff_user:Ganesha0024@cluster0.udkcjjn.mongodb.net/?appName=Cluster0"
DB_NAME = "stauff_sync_cache"
COLL_NAME = "overrides"
_OVERRIDE_TTL_SECONDS = 600  # 10 minutes

_mongo_client = None
def _get_collection():
    global _mongo_client
    if _mongo_client is None:
        try:
            _mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        except Exception as e:
            logger.error(f"[cloud_sync] Failed to connect to MongoDB: {e}")
            return None
    try:
        return _mongo_client[DB_NAME][COLL_NAME]
    except Exception as e:
        logger.error(f"[cloud_sync] Failed to get collection: {e}")
        return None

def _write_override_async(doc_id: str, doc_type: str, updates: dict):
    """Writes an override to MongoDB in a background thread to avoid blocking UI."""
    def _run():
        coll = _get_collection()
        if coll is None:
            return
        try:
            # We store task_id/goal_id as the _id, along with type and timestamp
            doc = {
                "_id": f"{doc_type}_{doc_id}",
                "type": doc_type,
                "target_id": doc_id,
                "updates": updates,
                "_ts": time.time()
            }
            # Use upsert to overwrite any existing pending override for this item
            coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)
            
            # Opportunistically clean up old overrides
            now = time.time()
            coll.delete_many({"_ts": {"$lt": now - _OVERRIDE_TTL_SECONDS}})
        except Exception as e:
            logger.error(f"[cloud_sync] Write failed: {e}")
            
    threading.Thread(target=_run, daemon=True).start()

def _get_all_overrides(doc_type: str) -> Dict[str, dict]:
    """Fetch all active overrides of a given type from MongoDB (blocking)."""
    coll = _get_collection()
    if coll is None:
        return {}
    
    try:
        now = time.time()
        # Find overrides for this type that are less than TTL seconds old
        cursor = coll.find({
            "type": doc_type,
            "_ts": {"$gte": now - _OVERRIDE_TTL_SECONDS}
        })
        
        result = {}
        for doc in cursor:
            result[doc["target_id"]] = doc.get("updates", {})
        return result
    except Exception as e:
        logger.error(f"[cloud_sync] Read failed: {e}")
        return {}


# ── Task overrides ──────────────────────────────────────────────────

def record_task_update(task_id: str, updates: dict):
    """
    Record an optimistic task update in the cloud so the other app sees it
    instantly without waiting for Google Sheets CDN.
    """
    _write_override_async(task_id, "task", updates)

def get_task_overrides() -> Dict[str, dict]:
    """Return all non-expired task overrides keyed by Task ID."""
    return _get_all_overrides("task")

def clear_task_override(task_id: str):
    """Remove a task override (e.g. once the Sheet data catches up)."""
    def _run():
        coll = _get_collection()
        if coll:
            try:
                coll.delete_one({"_id": f"task_{task_id}"})
            except Exception:
                pass
    threading.Thread(target=_run, daemon=True).start()


# ── Goal overrides ──────────────────────────────────────────────────

def record_goal_update(goal_id: str, updates: dict):
    """Record a cloud optimistic goal update."""
    _write_override_async(goal_id, "goal", updates)

def get_goal_overrides() -> Dict[str, dict]:
    """Return all non-expired goal overrides keyed by Goal ID."""
    return _get_all_overrides("goal")


# ── Merge helpers ───────────────────────────────────────────────────

def merge_task_overrides_into_list(tasks: list) -> list:
    """
    Apply cloud overrides onto a list of Task objects (models.data_models.Task).
    Fields in the override dict replace the corresponding Task attributes.
    """
    overrides = get_task_overrides()
    if not overrides:
        return tasks

    field_map = {
        "Status": "status",
        "Reason": "reason",
        "Deadline": "deadline",
        "Priority": "priority",
        "Updated By": "updated_by",
        "Last Updated": "last_updated",
    }

    for task in tasks:
        tid = getattr(task, "task_id", None) or getattr(task, "id", None)
        if tid and tid in overrides:
            override = overrides[tid]
            for json_key, attr_name in field_map.items():
                if json_key in override:
                    setattr(task, attr_name, override[json_key])

    return tasks

def merge_repo_task_overrides(tasks: list) -> list:
    """
    Apply cloud overrides onto a list of repository Task objects
    (Stauff_Task_Orch/data/models.py Task — uses .id, .status, .reason etc.).
    """
    overrides = get_task_overrides()
    if not overrides:
        return tasks

    field_map = {
        "Status": "status",
        "Reason": "reason",
        "Deadline": "due_date",
        "Priority": "priority",
    }

    for task in tasks:
        tid = getattr(task, "id", None)
        if tid and tid in overrides:
            override = overrides[tid]
            for json_key, attr_name in field_map.items():
                if json_key in override:
                    setattr(task, attr_name, override[json_key])

    return tasks

def merge_goal_overrides_into_list(goals: list) -> list:
    """Apply cloud overrides onto a list of Goal objects."""
    overrides = get_goal_overrides()
    if not overrides:
        return goals

    field_map = {
        "Status": "status",
        "Reason": "reason",
        "Deadline": "deadline",
        "Priority": "priority",
        "Updated By": "updated_by",
        "Last Updated": "last_updated",
    }

    for goal in goals:
        gid = getattr(goal, "goal_id", None) or getattr(goal, "id", None)
        if gid and gid in overrides:
            override = overrides[gid]
            for json_key, attr_name in field_map.items():
                if json_key in override:
                    setattr(goal, attr_name, override[json_key])

    return goals
