import csv
import io
import os
import glob
import uuid
import logging
import threading
import requests
from abc import ABC, abstractmethod
import pymongo
from typing import List, Dict, Callable, Optional
from collections import defaultdict

from .models import Person, Task, Goal, Update, SalesOrder

logger = logging.getLogger(__name__)

# Base department mapping from app.py
TEAM_STRUCTURE = {
    "SO department": ["Shreyash"],
    "PO department": ["Ganesh"],
    "Sales Department": ["Shruti"],
    "Logistics Department": ["Vaishnavi"]
}

# Published Google Sheet GIDs (from n8n workflow)
SHEET_GIDS = {
    "Boss": "0",
    "Tasks": "1931533029",
    "Goals": "1837353468"
}


def get_department(name: str) -> str:
    nl = name.lower()
    for dept, members in TEAM_STRUCTURE.items():
        if dept.lower() in nl or any(member.lower() in nl for member in members):
            return dept
            
    if "so " in nl or "so department" in nl: return "SO department"
    if "po " in nl or "po department" in nl: return "PO department"
    if "sales" in nl: return "Sales Department"
    if "logistics" in nl: return "Logistics Department"
    
    return "Other"


def normalize_name(name: str) -> str:
    if not name:
        return name
    nl = name.lower()
    for dept, members in TEAM_STRUCTURE.items():
        for member in members:
            if member.lower() in nl:
                return member
    return name


class DataRepository(ABC):
    @abstractmethod
    def get_tasks(self) -> List[Task]:
        pass

    @abstractmethod
    def get_goals(self) -> List[Goal]:
        pass

    @abstractmethod
    def get_updates(self) -> List[Update]:
        pass

    @abstractmethod
    def get_people(self) -> List[Person]:
        pass

    @abstractmethod
    def get_sales_orders(self) -> List[SalesOrder]:
        pass

    @abstractmethod
    def refresh(self):
        pass


class CSVRepository(DataRepository):
    """Loads data from local CSV files."""
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.tasks: List[Task] = []
        self.goals: List[Goal] = []
        self.updates: List[Update] = []
        self.people: List[Person] = []
        self.sales_orders: List[SalesOrder] = []
        self._load_data()

    def refresh(self):
        self.tasks.clear()
        self.goals.clear()
        self.updates.clear()
        self.people.clear()
        self.sales_orders.clear()
        self._load_data()

    def _load_data(self):
        self._load_boss_csv()
        self._load_goals_csv()
        self._load_individual_csvs()
        self._build_people()

    def _build_people(self):
        names = set()
        for t in self.tasks:
            names.add(t.person)
        for g in self.goals:
            names.add(g.person)
        for u in self.updates:
            names.add(u.person)
        for name in names:
            if name.lower() != "boss":
                dept = get_department(name)
                self.people.append(Person(name=name, department=dept))

    def _load_boss_csv(self):
        pattern = os.path.join(self.data_dir, "*Boss*.csv")
        files = glob.glob(pattern)
        if not files:
            return
        file_path = files[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date = row.get("Date", "").strip()
                    name = row.get("Name", "").strip() or row.get("Assigned To", "").strip()
                    name = normalize_name(name)
                    report = row.get("Report", "").strip()
                    rating = row.get("Rating", "").strip()
                    if date and name and report:
                        self.updates.append(Update(
                            id=str(uuid.uuid4()), date=date, person=name,
                            department=get_department(name), report=report, rating=rating
                        ))
        except Exception as e:
            logger.error(f"Error loading Boss CSV: {e}")

    def _load_goals_csv(self):
        pattern = os.path.join(self.data_dir, "*Goals*.csv")
        files = glob.glob(pattern)
        if not files:
            return
        file_path = files[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    timeframe = row.get("Time Frame", "").strip()
                    period = row.get("Week/Month", "").strip()
                    name = row.get("Assigned To", "").strip() or row.get("Name", "").strip()
                    name = normalize_name(name)
                    goal_text = row.get("Goal", "").strip() or row.get("Goals", "").strip()
                    given_by = row.get("Given By", "").strip()
                    status = row.get("Status", "Pending").strip()
                    reason = row.get("Reason", "").strip()
                    if timeframe and name and goal_text:
                        self.goals.append(Goal(
                            id=str(uuid.uuid4()), person=name,
                            department=get_department(name),
                            timeframe=timeframe, period=period, goal=goal_text,
                            given_by=given_by, status=status, reason=reason
                        ))
        except Exception as e:
            logger.error(f"Error loading Goals CSV: {e}")

    def _load_individual_csvs(self):
        pattern = os.path.join(self.data_dir, "*.csv")
        files = glob.glob(pattern)
        for file_path in files:
            filename = os.path.basename(file_path).lower()
            if "boss" in filename or "goals" in filename:
                continue
            base_name = os.path.basename(file_path).split('.')[0]
            parts = base_name.split('-')
            if len(parts) > 1:
                name_part = parts[1].split('(')[0].strip()
            else:
                name_part = base_name.split('(')[0].strip()
            person = normalize_name(name_part)
            dept = get_department(person)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        date = row.get("Date", "").strip()
                        task_text = row.get("Task Description", "").strip() or row.get("Tomorrow's Tasks", "").strip()
                        status = row.get("Status", "Pending").strip() or "Pending"
                        reason = row.get("Reason", "").strip()
                        source = row.get("Source", "").strip()
                        due_date = row.get("Deadline", "").strip()
                        task_id = row.get("Task ID", "").strip() or str(uuid.uuid4())
                        if date and task_text:
                            self.tasks.append(Task(
                                id=task_id, date=date, person=person,
                                department=dept, task=task_text,
                                status=status,
                                due_date=due_date,
                                reason=reason, source=source
                            ))
            except Exception as e:
                logger.error(f"Error loading individual CSV {file_path}: {e}")

    def get_tasks(self) -> List[Task]:
        return self.tasks

    def get_goals(self) -> List[Goal]:
        return self.goals

    def get_updates(self) -> List[Update]:
        return self.updates

    def get_people(self) -> List[Person]:
        return self.people

    def get_sales_orders(self) -> List[SalesOrder]:
        return self.sales_orders


class GoogleSheetRepository(DataRepository):
    """Fetches data live from a published Google Sheet."""

    def __init__(self, base_url: str, on_refresh_done: Optional[Callable] = None):
        self.base_url = base_url  # The published sheet base URL (without gid)
        self.on_refresh_done = on_refresh_done
        self.tasks: List[Task] = []
        self.goals: List[Goal] = []
        self.updates: List[Update] = []
        self.people: List[Person] = []
        self.sales_orders: List[SalesOrder] = []
        
        # Initialize MongoDB Client
        try:
            self.mongo_client = pymongo.MongoClient("mongodb+srv://stauff_user:Ganesha0024@cluster0.udkcjjn.mongodb.net/?appName=Cluster0", serverSelectionTimeoutMS=5000)
        except Exception as e:
            logger.error(f"Error initializing MongoDB client: {e}")
            self.mongo_client = None

        self._loading = False
        self.refresh()

    def _fetch_csv(self, gid: str) -> List[Dict[str, str]]:
        """Fetch a single sheet tab by GID and return rows as list of dicts."""
        import time
        url = f"{self.base_url}?gid={gid}&single=true&output=csv&_={int(time.time())}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            text = resp.text
            reader = csv.DictReader(io.StringIO(text))
            return list(reader)
        except Exception as e:
            logger.error(f"Error fetching GID {gid}: {e}")
            return []

    def refresh(self):
        """Re-fetch all data from Google Sheets."""
        if self._loading:
            return
        self._loading = True
        try:
            new_tasks: List[Task] = []
            new_goals: List[Goal] = []
            new_updates: List[Update] = []
            new_sales_orders: List[SalesOrder] = []

            # Fetch Boss (updates)
            boss_rows = self._fetch_csv(SHEET_GIDS["Boss"])
            for row in boss_rows:
                date = row.get("Date", "").strip()
                name = row.get("Name", "").strip() or row.get("Assigned To", "").strip()
                name = normalize_name(name)
                report = row.get("Report", "").strip()
                rating = row.get("Rating", "").strip()
                if date and name and report:
                    new_updates.append(Update(
                        id=str(uuid.uuid4()), date=date, person=name,
                        department=get_department(name), report=report, rating=rating
                    ))

            # Fetch Goals
            goals_rows = self._fetch_csv(SHEET_GIDS["Goals"])
            for row in goals_rows:
                timeframe = row.get("Time Frame", "").strip()
                period = row.get("Week/Month", "").strip()
                name = row.get("Assigned To", "").strip() or row.get("Name", "").strip()
                name = normalize_name(name)
                goal_text = row.get("Goal", "").strip() or row.get("Goals", "").strip()
                given_by = row.get("Given By", "").strip()
                status = row.get("Status", "Pending").strip()
                reason = row.get("Reason", "").strip()
                if timeframe and name and goal_text:
                    new_goals.append(Goal(
                        id=str(uuid.uuid4()), person=name,
                        department=get_department(name),
                        timeframe=timeframe, period=period, goal=goal_text,
                        given_by=given_by, status=status, reason=reason
                    ))

            # Fetch individual tasks from unified Tasks sheet
            tasks_rows = self._fetch_csv(SHEET_GIDS["Tasks"])
            for row in tasks_rows:
                date = row.get("Date", "").strip()
                task_text = row.get("Task Description", "").strip() or row.get("Tomorrow's Tasks", "").strip()
                person_name = row.get("Assigned To", "").strip()
                person_name = normalize_name(person_name) if person_name else person_name
                dept = row.get("Department", "").strip() or get_department(person_name)
                status = row.get("Status", "Pending").strip() or "Pending"
                reason = row.get("Reason", "").strip()
                source = row.get("Source", "").strip()
                due_date = row.get("Deadline", "").strip()
                task_id = row.get("Task ID", "").strip() or str(uuid.uuid4())
                if date and task_text:
                    new_tasks.append(Task(
                        id=task_id, date=date, person=person_name,
                        department=dept, task=task_text,
                        status=status,
                        due_date=due_date,
                        reason=reason, source=source
                    ))

            # Fetch Sales Orders from MongoDB
            if self.mongo_client:
                try:
                    db = self.mongo_client['stauff_so_system']
                    
                    purchase_orders = {str(po["_id"]): po for po in db["purchase_orders"].find()}
                    po_docs = {doc["document_fingerprint"]: doc for doc in db["po_documents"].find()}
                    
                    # Temporarily fetching all po_items (even if created_by is missing) for visibility
                    # Adjust query back to {"created_by": {"$exists": True}} if required
                    cursor = db['po_items'].find() 
                    seen_pos = {}
                    for doc in cursor:
                        so_number = doc.get("po_number", "Unknown")
                        company = doc.get("company_name", "Unknown")
                        time_val = str(doc.get("created_at", ""))
                        
                        created_by = doc.get("created_by", {})
                        person = created_by.get("user_id", "Unknown")
                        person = normalize_name(person)
                        
                        po_id = doc.get("po_id")
                        po_obj = purchase_orders.get(po_id, {})
                        fingerprint = po_obj.get("document_fingerprint")
                        doc_obj = po_docs.get(fingerprint, {})
                        
                        link = doc_obj.get("retained_path", "")
                        filename = doc_obj.get("original_filename", "")
                        
                        item_info = f"{doc.get('qty', 0)}x {doc.get('stauff_code', 'Unknown')}"
                        
                        dedup_key = f"{person}_{so_number}"
                        if dedup_key not in seen_pos:
                            seen_pos[dedup_key] = SalesOrder(
                                id=str(doc.get("_id", uuid.uuid4())),
                                po_number=so_number,
                                company_name=company,
                                time=time_val,
                                person=person,
                                link=link,
                                filename=filename,
                                items_data=item_info
                            )
                        else:
                            seen_pos[dedup_key].items_data += f"\n{item_info}"
                            
                    for so in seen_pos.values():
                        new_sales_orders.append(so)
                except Exception as e:
                    logger.error(f"Error fetching Sales Orders from MongoDB: {e}")

            # Atomically swap
            self.tasks = new_tasks
            self.goals = new_goals
            self.updates = new_updates
            self.sales_orders = new_sales_orders
            self._rebuild_people()

        except Exception as e:
            logger.error(f"Error during Google Sheet refresh: {e}")
        finally:
            self._loading = False

    def refresh_async(self):
        """Refresh in a background thread."""
        def _run():
            self.refresh()
            if self.on_refresh_done:
                self.on_refresh_done()
        threading.Thread(target=_run, daemon=True).start()

    def _rebuild_people(self):
        real_names = []
        for members in TEAM_STRUCTURE.values():
            real_names.extend([m.lower() for m in members])
            
        names = set()
        for t in self.tasks:
            names.add(t.person)
        for g in self.goals:
            names.add(g.person)
        for u in self.updates:
            names.add(u.person)
            
        new_people = []
        for name in names:
            if name.lower() in real_names:
                new_people.append(Person(name=name, department=get_department(name)))
        self.people = new_people

    def get_tasks(self) -> List[Task]:
        return self.tasks

    def get_goals(self) -> List[Goal]:
        return self.goals

    def get_updates(self) -> List[Update]:
        return self.updates

    def get_people(self) -> List[Person]:
        return self.people

    def get_sales_orders(self) -> List[SalesOrder]:
        return self.sales_orders
