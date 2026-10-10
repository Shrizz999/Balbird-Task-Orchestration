import json

with open('Stauff - Extension Requests.json', 'r', encoding='utf8') as f:
    wf = json.load(f)

for node in wf['nodes']:
    if node['type'] == 'n8n-nodes-base.supabase':
        print(f"{node['name']}: {node['parameters'].get('operation')}")
