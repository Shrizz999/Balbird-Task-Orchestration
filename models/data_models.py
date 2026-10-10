from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Goal:
    goal_id: str
    time_frame: str
    week_month: str # Used as Goal Date or Month
    assigned_to: str
    given_by: str
    goal: str
    deadline: str
    status: str
    reason: str = ""
    priority: str = "Normal"
    updated_by: str = ""
    last_updated: str = ""
    checklist: list = field(default_factory=list)

@dataclass
class Task:
    task_id: str
    date: str
    description: str
    assigned_to: str
    assigned_by: str
    deadline: str
    status: str
    reason: str = ""
    priority: str = "Normal"
    source: str = ""
    updated_by: str = ""
    last_updated: str = ""
    checklist: list = field(default_factory=list)

@dataclass
class Report:
    date: str
    name: str
    report: str
    rating: str
