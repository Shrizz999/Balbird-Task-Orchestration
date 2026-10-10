import os

repo_path = 'c:/Programming/Stauff_TO_v2/Stauff_Task_Orch/data/repository.py'
with open(repo_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_class = '''
class SupabaseRepository(DataRepository):
    def __init__(self, base_url: str, api_key: str, on_refresh_done=None):
        self.base_url = f"{base_url}/rest/v1"
        self.headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.on_refresh_done = on_refresh_done
        self.tasks = []
        self.goals = []
        self.updates = []
        self.people = []
        self.sales_orders = []
        self._loading = False
        self.refresh()

    def _fetch_table(self, table_name: str):
        if not self.base_url or 'your-project' in self.base_url:
            return []
        url = f"{self.base_url}/{table_name}?select=*"
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error fetching {table_name} from Supabase: {e}")
            return []

    def refresh(self):
        if self._loading: return
        self._loading = True
        try:
            new_tasks = []
            new_goals = []
            
            raw_tasks = self._fetch_table('tasks')
            for row in raw_tasks:
                person = normalize_name(row.get('assigned_to', ''))
                dept = row.get('department', '') or get_department(person)
                new_tasks.append(Task(
                    id=row.get('task_id', ''), date=row.get('date', ''),
                    person=person, department=dept, task=row.get('description', ''),
                    status=row.get('status', 'Pending'), due_date=row.get('deadline', ''),
                    reason=row.get('reason', ''), source=row.get('source', '')
                ))

            raw_goals = self._fetch_table('monthly_goals')
            for row in raw_goals:
                person = normalize_name(row.get('assigned_to', ''))
                dept = get_department(person)
                new_goals.append(Goal(
                    id=row.get('goal_id', ''), person=person, department=dept,
                    timeframe=row.get('time_frame', ''), period=row.get('week_month', ''),
                    goal=row.get('goal', ''), given_by=row.get('given_by', ''),
                    status=row.get('status', 'Pending'), reason=row.get('reason', '')
                ))

            self.tasks = merge_repo_task_overrides(new_tasks)
            self.goals = new_goals
            self._rebuild_people()

        except Exception as e:
            logger.error(f"Supabase refresh error: {e}")
        finally:
            self._loading = False

    def refresh_async(self):
        def _run():
            self.refresh()
            if self.on_refresh_done: self.on_refresh_done()
        threading.Thread(target=_run, daemon=True).start()

    def _rebuild_people(self):
        names = set()
        for members in TEAM_STRUCTURE.values():
            for member in members:
                names.add(member)
        for t in self.tasks:
            if t.person: names.add(t.person)
        for g in self.goals:
            if g.person: names.add(g.person)
        new_people = []
        for name in names:
            if name:
                new_people.append(Person(name=name, department=get_department(name)))
        self.people = sorted(new_people, key=lambda p: p.name)

    def get_tasks(self) -> List[Task]: return self.tasks
    def get_goals(self) -> List[Goal]: return self.goals
    def get_updates(self) -> List[Update]: return self.updates
    def get_people(self) -> List[Person]: return self.people
    def get_sales_orders(self) -> List[SalesOrder]: return self.sales_orders
'''

if 'class SupabaseRepository' not in content:
    content += '\n' + new_class

with open(repo_path, 'w', encoding='utf-8') as f:
    f.write(content)
