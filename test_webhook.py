import requests
import json
import time

webhook_url = "https://n8n.srv1463077.hstgr.cloud/form/280e1709-fbed-4560-a10c-9f96956654b8"
payload = {
    "individual_updates": [
        {
            "Task ID": "TSK-261001-SHR-TEST",
            "Date": "01/10/2026",
            "Task Description": "Test Task",
            "Assigned To": "Shreyash",
            "Assigned By": "Manager",
            "Deadline": "05/10/2026",
            "Priority": "Normal",
            "Status": "Completed",
            "Reason": "Done",
            "Source": "Manual",
            "Updated By": "UI Input",
            "Last Updated": "2026-10-01T12:00:00Z"
        }
    ]
}

form_data = {
    "field-0": (None, "Live Updates"),
    "field-1": (None, json.dumps(payload))
}

print("Sending request...")
resp = requests.post(webhook_url, files=form_data)
print("Status Code:", resp.status_code)
print("Response:", resp.text)
