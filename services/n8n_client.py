import json
import requests
from config import N8N_WEBHOOK_URL, N8N_MONTHLY_UPDATES_WEBHOOK_URL, N8N_EXTENSION_WEBHOOK_URL, N8N_TASK_PROGRESS_WEBHOOK_URL

class N8nClient:
    def __init__(self, webhook_url: str = N8N_WEBHOOK_URL):
        self.webhook_url = webhook_url
        self.extension_webhook_url = N8N_EXTENSION_WEBHOOK_URL
        self.task_progress_webhook_url = N8N_TASK_PROGRESS_WEBHOOK_URL


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



    def submit_extension_request(self, request_data: dict) -> bool:
        """
        Submit a new extension request.
        request_data: { "action": "submit", "id": "...", "task_id": "...", ... }
        """
        try:
            resp = requests.post(self.extension_webhook_url, json=request_data, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            raise Exception(f"Failed to submit extension request: {str(e)}")

    def submit_extension_decision(self, decision_data: dict) -> bool:
        """
        Submit a manager decision on an extension request.
        decision_data: { "action": "decide", "id": "...", "status": "Approved/Rejected", ... }
        """
        try:
            resp = requests.post(self.extension_webhook_url, json=decision_data, timeout=30)
            resp.raise_for_status()
            return True
        except Exception as e:
            raise Exception(f"Failed to submit extension decision: {str(e)}")


    def submit_task_progress_update(
        self,
        task_id: str,
        update_text: str,
        current_checklist: list,
        task_description: str = "",
        employee_name: str = "",
        current_status: str = "Pending"
    ) -> dict:
        """
        Sends employee's progress description for a task to n8n to interpret against the checklist.
        Returns the parsed response from n8n with updated checklist and status.
        """
        payload = {
            "task_id": task_id,
            "update_text": update_text,
            "current_checklist": current_checklist or [],
            "task_description": task_description or "",
            "employee_name": employee_name or "",
            "status": current_status or "Pending"
        }
        try:
            resp = requests.post(self.task_progress_webhook_url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            if isinstance(data, dict):
                data.setdefault("success", True)
                return data
            return {"success": True, "raw_response": data}
        except Exception as e:
            raise Exception(f"Failed to submit task progress to n8n: {str(e)}")

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
