import json
import requests
from config import N8N_WEBHOOK_URL, N8N_MONTHLY_UPDATES_WEBHOOK_URL

class N8nClient:
    def __init__(self, webhook_url: str = N8N_WEBHOOK_URL):
        self.webhook_url = webhook_url

    def submit_daily_goals(self, goals_dict: dict) -> bool:
        """
        goals_dict: { "Shreyash": [{"goal": "...", "date": "...", "deadline": "...", "priority": "..."}] }
        """
        payload = {
            "goals": goals_dict
        }
        return self._send_to_n8n("Daily Goals", payload)

    def submit_monthly_goals(self, goals_dict: dict) -> bool:
        """
        goals_dict: { "SO department": [{"goal": "...", "month": "...", "deadline": "...", "priority": "..."}] }
        """
        payload = {
            "goals": goals_dict
        }
        return self._send_to_n8n("Monthly Goals", payload)

    def submit_transcript(self, transcript: str) -> bool:
        payload = {
            "transcript": transcript
        }
        return self._send_to_n8n("Daily Transcript", payload)

    def submit_live_updates(self, individual_updates: list) -> bool:
        """
        individual_updates: [ { "Task ID": "...", "Status": "...", ... } ]
        """
        payload = {
            "individual_updates": individual_updates
        }
        return self._send_to_n8n("Live Updates", payload)

    def submit_goals_updates(self, individual_updates: list) -> bool:
        payload = {
            "individual_updates": individual_updates
        }
        try:
            resp = requests.post(N8N_MONTHLY_UPDATES_WEBHOOK_URL, json=payload, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            raise Exception(f"Failed to communicate with n8n: {str(e)}")



    def _send_to_n8n(self, mode: str, payload: dict) -> bool:
        form_data = {
            "field-0": (None, mode),
            "field-1": (None, json.dumps(payload))
        }
        try:
            # Short timeout since Form Trigger responds instantly
            resp = requests.post(self.webhook_url, files=form_data, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            raise Exception(f"Failed to communicate with n8n: {str(e)}")
