import requests
from typing import List, Dict
from config import SUPABASE_URL, SUPABASE_KEY
from models.data_models import Goal, Task, Report
from services.local_sync import merge_task_overrides_into_list, merge_goal_overrides_into_list

class SupabaseClient:
    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }

    def _fetch_table(self, table_name: str) -> List[Dict]:
        if not SUPABASE_URL or not SUPABASE_KEY or "your-project" in SUPABASE_URL:
            print("Supabase credentials not set.")
            return []
            
        url = f"{self.base_url}/{table_name}?select=*"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching data from {table_name}: {e}")
            return []

    def fetch_all_goals(self) -> List[Goal]:
        raw_data = self._fetch_table("monthly_goals")
        goals = []
        for row in raw_data:
            goals.append(Goal(
                goal_id=row.get("goal_id", ""),
                time_frame=row.get("time_frame", ""),
                week_month=row.get("week_month", ""),
                assigned_to=row.get("assigned_to", ""),
                given_by=row.get("given_by", ""),
                goal=row.get("goal", ""),
                deadline=row.get("deadline", ""),
                status=row.get("status", "Pending"),
                reason=row.get("reason", ""),
                priority="Normal", # Priority might not exist on monthly_goals schema, default
                updated_by=row.get("updated_by", ""),
                last_updated=row.get("last_updated", ""),
                checklist=row.get("checklist", [])
            ))
        return merge_goal_overrides_into_list(goals)

    def fetch_daily_goals(self) -> List[Goal]:
        return [g for g in self.fetch_all_goals() if g.time_frame == "Daily"]

    def fetch_monthly_goals(self) -> List[Goal]:
        return [g for g in self.fetch_all_goals() if g.time_frame == "Monthly"]

    def fetch_tasks_for_employee(self, employee_name: str) -> List[Task]:
        return [t for t in self.fetch_all_tasks() if employee_name.lower() in t.assigned_to.lower()]

    def fetch_all_tasks(self) -> List[Task]:
        raw_data = self._fetch_table("tasks")
        tasks = []
        for row in raw_data:
            tasks.append(Task(
                task_id=row.get("task_id", ""),
                date=row.get("date", ""),
                description=row.get("description", ""),
                assigned_to=row.get("assigned_to", ""),
                assigned_by=row.get("assigned_by", ""),
                deadline=row.get("deadline", ""),
                status=row.get("status", "Pending"),
                reason=row.get("reason", ""),
                priority=row.get("priority", "Normal"),
                source=row.get("source", ""),
                updated_by=row.get("updated_by", ""),
                last_updated=row.get("last_updated", ""),
                checklist=row.get("checklist", [])
            ))
        tasks = merge_task_overrides_into_list(tasks)
        from datetime import datetime
        for t in tasks:
            if t.status and t.status.lower() not in ("completed", "done", "update") and t.deadline:
                for fmt in ("%d/%m/%Y", "%d/%m", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
                    try:
                        dt = datetime.strptime(str(t.deadline).strip(), fmt)
                        if (datetime.now().date() - dt.date()).days > 0:
                            t.status = "Delayed"
                        break
                    except (ValueError, AttributeError):
                        continue
        return tasks

    def update_task_checklist(self, task_id: str, checklist: list, status: str = None, updated_by: str = None) -> bool:
        if not SUPABASE_URL or not SUPABASE_KEY or "your-project" in SUPABASE_URL:
            return False
        url = f"{self.base_url}/tasks?task_id=eq.{task_id}"
        payload = {"checklist": checklist}
        if status:
            payload["status"] = status
        if updated_by:
            payload["updated_by"] = updated_by
        try:
            headers = self.headers.copy()
            headers["Prefer"] = "return=minimal"
            response = requests.patch(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error updating checklist: {e}")
            return False


    def update_monthly_goal_checklist(self, goal_id: str, checklist: list) -> bool:
        if not SUPABASE_URL or not SUPABASE_KEY or "your-project" in SUPABASE_URL:
            return False
        url = f"{self.base_url}/monthly_goals?goal_id=eq.{goal_id}"
        payload = {"checklist": checklist}
        try:
            headers = self.headers.copy()
            headers["Prefer"] = "return=minimal"
            response = requests.patch(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error updating monthly goal checklist: {e}")
            return False

    def fetch_boss_reports(self) -> List[Report]:
        # If boss reports are needed in Supabase, they'd be fetched here
        # Assuming you will use tasks table or a separate boss_reports table
        raw_data = self._fetch_table("boss_reports")
        reports = []
        for row in raw_data:
            reports.append(Report(
                date=row.get("date", ""),
                name=row.get("name", ""),
                report=row.get("report", ""),
                rating=row.get("rating", "")
            ))
        return reports
