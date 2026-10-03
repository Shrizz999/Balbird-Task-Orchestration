import sys
import os
from services.n8n_client import N8nClient
from datetime import datetime

try:
    n8n = N8nClient()
    update_payload = {
        "Task ID": "TSK-260927-SHR-JB15",
        "Date": "27/09",
        "Task Description": "Demo task mana",
        "Assigned To": "Shreyash",
        "Assigned By": "Manager",
        "Deadline": "07/10/2026",
        "Priority": "Normal",
        "Status": "Pending",
        "Reason": "Test script extension",
        "Source": "Meeting Transcript",
        "Updated By": "Manager UI",
        "Last Updated": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    print("Sending payload...", update_payload)
    success = n8n.submit_live_updates([update_payload])
    print("Success:", success)
except Exception as e:
    print(f"Failed to update Google Sheet via n8n: {e}")
