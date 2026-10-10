import requests, json, sys
sys.path.insert(0, 'c:/Programming/Stauff_TO_v2')
from config import SUPABASE_URL, SUPABASE_KEY

headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}'
}

print('--- TASKS ---')
try:
    resp = requests.get(f'{SUPABASE_URL}/rest/v1/tasks?select=*', headers=headers)
    tasks = resp.json()
    for t in tasks[-5:]:
        print(f"{t.get('task_id')}: assigned_to={t.get('assigned_to')}, dept={t.get('department')}, desc={t.get('description')}")
except Exception as e:
    print('error', e)

print('\n--- MONTHLY GOALS ---')
try:
    resp = requests.get(f'{SUPABASE_URL}/rest/v1/monthly_goals?select=*', headers=headers)
    goals = resp.json()
    for g in goals[-5:]:
        print(f"{g.get('goal_id')}: assigned_to={g.get('assigned_to')}, goal={g.get('goal')}")
except Exception as e:
    print('error', e)
