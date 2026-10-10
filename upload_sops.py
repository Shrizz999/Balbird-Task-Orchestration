import os
import sys
import json
import requests
from config import SUPABASE_URL, SUPABASE_KEY

# Setup REST headers for Supabase
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def upload_sops():
    file_path = "ALL_SOPS.md"
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found in the current directory.")
        return

    with open(file_path, "r", encoding="utf8") as f:
        content = f.read()

    # Split the content into sections, or just upload the whole document as one SOP.
    # Since the user stated "these are my SOPs for just SO department", we can upload 
    # the entire document under the "SO department".
    
    payload = {
        "department": "SO department",
        "task_type": "General SOPs",
        "content": content
    }

    print("Uploading SOPs for SO department to Supabase...")
    
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/company_sops",
        headers=headers,
        json=payload
    )

    if response.status_code in [201, 200, 204]:
        print("Successfully uploaded SOPs to the database!")
    else:
        print(f"Failed to upload. Status: {response.status_code}")
        print("Response:", response.text)

if __name__ == "__main__":
    upload_sops()
