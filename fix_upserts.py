import json

file_path = 'c:/Programming/Stauff_TO_v2/Stauff - Extension Requests.json'
with open(file_path, 'r', encoding='utf8') as f:
    wf = json.load(f)

# Nodes that are creating completely NEW records
insert_nodes = [
    "Upsert Tasks (Daily Goals)",
    "Upsert Tasks (Transcript)",
    "Upsert Monthly Goals",
    "Append Boss",
    "Append Extension Request"
]

# Nodes that are modifying EXISTING records based on an ID
update_nodes = [
    "Upsert Tasks (Live Updates)",
    "Update Goals Sheet",
    "Upsert Goals from Updates",
    "Update Extension Decision"
]

for node in wf['nodes']:
    if node['type'] == 'n8n-nodes-base.supabase':
        node_name = node['name']
        if node_name in insert_nodes:
            node['parameters']['operation'] = 'insert'
        elif node_name in update_nodes:
            node['parameters']['operation'] = 'update'
            # For update operations, n8n usually needs to know what column to match on
            # Adding a placeholder matchColumn if the user needs it
            if 'options' not in node['parameters']:
                node['parameters']['options'] = {}

with open(file_path, 'w', encoding='utf8') as f:
    json.dump(wf, f, indent=2)

print("Changed upserts to explicit inserts and updates.")
