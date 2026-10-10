import json

file_path = 'c:/Programming/Stauff_TO_v2/Stauff - Extension Requests.json'
with open(file_path, 'r', encoding='utf8') as f:
    wf = json.load(f)

for node in wf['nodes']:
    if node['type'] == 'n8n-nodes-base.supabase':
        op = node['parameters'].get('operation')
        if op == 'insert':
            node['parameters']['operation'] = 'create'
        elif op == 'getAll':
            node['parameters']['operation'] = 'getMany'

with open(file_path, 'w', encoding='utf8') as f:
    json.dump(wf, f, indent=2)

print("Updated Supabase operations to 'create' and 'getMany'")
