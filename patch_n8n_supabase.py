import json

file_path = 'c:/Programming/Stauff_TO_v2/Stauff - Extension Requests.json'
with open(file_path, 'r', encoding='utf8') as f:
    wf = json.load(f)

# Convert all Postgres nodes to Supabase nodes
for node in wf['nodes']:
    if node['type'] == 'n8n-nodes-base.postgres':
        node['type'] = 'n8n-nodes-base.supabase'
        node['typeVersion'] = 1
        
        # If it was the Fetch SOPs node
        if node['name'] == 'Fetch SOPs':
            node['parameters'] = {
                "operation": "getAll",
                "tableId": "company_sops",
                "options": {}
            }
        else:
            # Upsert nodes
            node['parameters'] = {
                "operation": "upsert",
                "tableId": "YOUR_TABLE_NAME",
                "options": {}
            }
            
        node['credentials'] = {
            "supabaseApi": {
                "id": "YOUR_SUPABASE_CRED_ID",
                "name": "Supabase API"
            }
        }

with open(file_path, 'w', encoding='utf8') as f:
    json.dump(wf, f, indent=2)

print("Updated workflow JSON successfully.")
