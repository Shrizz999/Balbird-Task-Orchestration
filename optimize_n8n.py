import json

file_path = 'c:/Programming/Stauff_TO_v2/Stauff - Extension Requests.json'
with open(file_path, 'r', encoding='utf8') as f:
    wf = json.load(f)

# Define mapping for node names to Supabase tables
table_mapping = {
    "Upsert Tasks (Daily Goals)": "tasks",
    "Upsert Tasks (Transcript)": "tasks",
    "Upsert Tasks (Live Updates)": "tasks",
    "Update Goals Sheet": "monthly_goals",
    "Upsert Monthly Goals": "monthly_goals",
    "Upsert Goals from Updates": "monthly_goals",
    "Append Boss": "tasks",
    "Append Extension Request": "extension_requests",
    "Update Extension Decision": "extension_requests",
    "Fetch Monthly Context": "monthly_goals",
    "Fetch All Tasks Context": "tasks",
    "Fetch SOPs": "company_sops"
}

for node in wf['nodes']:
    # 1. Optimize Webhooks to return immediately (0ms delay for the Python Exe)
    if node['type'] == 'n8n-nodes-base.webhook':
        if 'parameters' not in node:
            node['parameters'] = {}
        node['parameters']['responseMode'] = 'onReceived'
        node['parameters']['responseData'] = 'empty'

    if node['type'] == 'n8n-nodes-base.formTrigger':
        if 'parameters' not in node:
            node['parameters'] = {}
        if 'options' not in node['parameters']:
            node['parameters']['options'] = {}
        node['parameters']['options']['responseMode'] = 'onReceived'

    # 2. Automap the correct tables to the Supabase nodes
    if node['type'] == 'n8n-nodes-base.supabase':
        node_name = node['name']
        if node_name in table_mapping:
            if 'parameters' not in node:
                node['parameters'] = {}
            node['parameters']['tableId'] = table_mapping[node_name]
            
            # For read nodes, configure them to getAll
            if node_name.startswith("Fetch"):
                node['parameters']['operation'] = 'getAll'
                node['parameters']['options'] = {}
            else:
                node['parameters']['operation'] = 'upsert'

with open(file_path, 'w', encoding='utf8') as f:
    json.dump(wf, f, indent=2)

print("Optimized workflow JSON for performance and mapped Supabase tables.")
