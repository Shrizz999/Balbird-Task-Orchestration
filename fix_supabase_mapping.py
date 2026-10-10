import json
import re

file_path = 'c:/Programming/Stauff_TO_v2/Stauff - Extension Requests.json'
with open(file_path, 'r', encoding='utf8') as f:
    wf = json.load(f)

replacements = {
    '"Task ID":': '"task_id":',
    '"Date":': '"date":',
    '"Task Description":': '"description":',
    '"Assigned To":': '"assigned_to":',
    '"Assigned By":': '"assigned_by":',
    '"Department":': '"department":',
    '"Deadline":': '"deadline":',
    '"Priority":': '"priority":',
    '"Status":': '"status":',
    '"Reason":': '"reason":',
    '"Source":': '"source":',
    '"Updated By":': '"updated_by":',
    '"Last Updated":': '"last_updated":',
    
    '"Goal ID":': '"goal_id":',
    '"Time Frame":': '"time_frame":',
    '"Week/Month":': '"week_month":',
    '"Goal":': '"goal":',
    '"Given By":': '"given_by":',
    
    '"ID":': '"request_id":',
    '"Employee":': '"employee_name":',
    '"Current Deadline":': '"current_deadline":',
    '"Requested Deadline":': '"requested_deadline":',
    '"Manager Deadline":': '"manager_deadline":',
    '"Manager Note":': '"manager_note":',
    '"Submitted At":': '"created_at":',
    '"Decided At":': '"decided_at":'
}

for node in wf['nodes']:
    # 1. Update JS Code nodes to output correct schema keys
    if node['type'] == 'n8n-nodes-base.code':
        if 'jsCode' in node['parameters']:
            code = node['parameters']['jsCode']
            for old, new in replacements.items():
                code = code.replace(old, new)
            node['parameters']['jsCode'] = code

    # 2. Update Supabase nodes to Auto Map Input Data
    if node['type'] == 'n8n-nodes-base.supabase':
        if 'dataMode' in node['parameters']:
            node['parameters']['dataMode'] = 'autoMapInputData'
        else:
            node['parameters']['dataMode'] = 'autoMapInputData'
            
        # Ensure match columns for update operations
        if node['parameters'].get('operation') == 'update':
            table = node['parameters'].get('tableId', '')
            if 'options' not in node['parameters']:
                node['parameters']['options'] = {}
            if table == 'tasks':
                node['parameters']['matchColumns'] = 'task_id'
            elif table == 'monthly_goals':
                node['parameters']['matchColumns'] = 'goal_id'
            elif table == 'extension_requests':
                node['parameters']['matchColumns'] = 'request_id'

with open(file_path, 'w', encoding='utf8') as f:
    json.dump(wf, f, indent=2)

print("Mapped JSON keys to Supabase columns and set dataMode to Auto Map.")
