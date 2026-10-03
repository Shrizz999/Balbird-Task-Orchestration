from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Person:
    name: str
    department: str

@dataclass
class Task:
    id: str
    date: str
    person: str
    department: str
    task: str
    goal: str = ""
    status: str = "Pending"
    priority: str = "Normal"
    so: str = ""
    po: str = ""
    due_date: str = ""
    reason: str = ""
    source: str = ""

@dataclass
class Goal:
    id: str
    person: str
    department: str
    timeframe: str  # "Weekly" or "Monthly"
    period: str     # e.g., "August, 2026"
    goal: str
    given_by: str = ""
    status: str = "Pending"
    reason: str = ""

@dataclass
class Update:
    id: str
    date: str
    person: str
    department: str
    report: str
    rating: Optional[str] = None

@dataclass
class SalesOrder:
    id: str
    po_number: str
    company_name: str
    time: str
    person: str
    link: str = ""
    filename: str = ""
    items_data: str = ""
