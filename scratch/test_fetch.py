import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import SUPABASE_URL, SUPABASE_KEY
import requests

url = f"{SUPABASE_URL}/rest/v1/boss_reviews?select=*"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

resp = requests.get(url, headers=headers)
print("Status:", resp.status_code)
print("Data:", resp.text)
