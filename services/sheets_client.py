import csv
import io
import os
from pathlib import Path
from typing import List, Dict
import requests
from config import CSV_FILES, USE_LOCAL_CSV, SHEET_BASE_URL, SHEET_GIDS
from models.data_models import Goal, Task, Report
from services.local_sync import merge_task_overrides_into_list, merge_goal_overrides_into_list

class SheetsClient:
    def __init__(self):
        pass

    def _fetch_csv_data(self, file_key: str) -> List[Dict]:
        if USE_LOCAL_CSV:
            path = CSV_FILES.get(file_key)
            if not path or not os.path.exists(path):
                return []
            try:
                with open(path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            except Exception as e:
                print(f"Failed to read local CSV {path}: {e}")
                return []
        else:
            gid = SHEET_GIDS.get(file_key)
            if not gid:
                return []
            import time
            url = f"{SHEET_BASE_URL}{gid}&_={int(time.time())}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                f = io.StringIO(response.text)
                reader = csv.DictReader(f)
                return list(reader)
            except Exception as e:
                print(f"Error fetching data for {file_key}: {e}")
                return []

    def fetch_all_goals(self) -> List[Goal]:
        raw_data = self._fetch_csv_data("Goals")
        goals = []
        for row in raw_data:
            if not row.get("Goal ID") and not row.get("Task ID"):
                continue
            goals.append(Goal(
                goal_id=row.get("Goal ID", row.get("Task ID", "")),
                time_frame=row.get("Time Frame", ""),
                week_month=row.get("Week/Month", ""),
                assigned_to=row.get("Assigned To", ""),
                given_by=row.get("Given By", row.get("Assigned By", "")),
                goal=row.get("Goal", row.get("Task Description", "")),
                deadline=row.get("Deadline", ""),
                status=row.get("Status", "Pending"),
                reason=row.get("Reason", ""),
                priority=row.get("Priority", "Normal"),
                updated_by=row.get("Updated By", ""),
                last_updated=row.get("Last Updated", "")
            ))
        return merge_goal_overrides_into_list(goals)

    def fetch_daily_goals(self) -> List[Goal]:
        return [g for g in self.fetch_all_goals() if g.time_frame == "Daily"]

    def fetch_monthly_goals(self) -> List[Goal]:
        return [g for g in self.fetch_all_goals() if g.time_frame == "Monthly"]

    def fetch_tasks_for_employee(self, employee_name: str) -> List[Task]:
        return [t for t in self.fetch_all_tasks() if t.assigned_to == employee_name]

    def fetch_all_tasks(self) -> List[Task]:
        raw_data = self._fetch_csv_data("Tasks")
        tasks = []
        for row in raw_data:
            if not row.get("Task ID"):
                continue
            tasks.append(Task(
                task_id=row.get("Task ID", ""),
                date=row.get("Date", ""),
                description=row.get("Task Description", ""),
                assigned_to=row.get("Assigned To", ""),
                assigned_by=row.get("Assigned By", ""),
                deadline=row.get("Deadline", ""),
                status=row.get("Status", "Pending"),
                reason=row.get("Reason", ""),
                priority=row.get("Priority", "Normal"),
                source=row.get("Source", ""),
                updated_by=row.get("Updated By", ""),
                last_updated=row.get("Last Updated", "")
            ))
        return merge_task_overrides_into_list(tasks)

    def fetch_boss_reports(self) -> List[Report]:
        raw_data = self._fetch_csv_data("Boss")
        reports = []
        for row in raw_data:
            reports.append(Report(
                date=row.get("Date", ""),
                name=row.get("Name", ""),
                report=row.get("Report", ""),
                rating=row.get("Rating", "")
            ))
        return reports
