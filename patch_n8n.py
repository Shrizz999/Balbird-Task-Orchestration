import json

file_path = 'c:/Programming/Stauff_TO_v2/Stauff - Extension Requests.json'
with open(file_path, 'r', encoding='utf8') as f:
    wf = json.load(f)

# 1. Update LLM Prompt to ask for checklist
for node in wf['nodes']:
    if node['name'] == 'Basic LLM Chain':
        messages = node['parameters']['messages']['messageValues']
        for msg in messages:
            if msg['type'] == 'HumanMessagePromptTemplate':
                old_msg = msg['message']
                if 'Checklist' not in old_msg:
                    new_msg = old_msg.replace('"Tasks" Schema:\n{', '"Tasks" Schema:\n{\n  "Checklist": ["Step 1", "Step 2", "..."], // AI Generated stepwise task checklist based on Company SOPs')
                    new_msg = new_msg.replace('CONTEXT:\n', 'CONTEXT:\nCompany SOPs: {{ JSON.stringify($json.sops || []) }}\n')
                    msg['message'] = new_msg

# 2. Update Extract & Map Tasks
    if node['name'] == 'Extract & Map Tasks':
        js = node['parameters']['jsCode']
        if 'Checklist:' not in js:
            js = js.replace('"Last Updated": new Date().toISOString() } };', '"Last Updated": new Date().toISOString(), "Checklist": t.Checklist || [] } };')
            node['parameters']['jsCode'] = js

# 3. Add Fetch SOPs node
sops_node_exists = any(n['name'] == 'Fetch SOPs' for n in wf['nodes'])
if not sops_node_exists:
    sops_node = {
        "parameters": {
            "operation": "executeQuery",
            "query": "SELECT * FROM company_sops",
            "options": {}
        },
        "id": "fetch-sops-postgres",
        "name": "Fetch SOPs",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.2,
        "position": [2864, 1880],
        "credentials": {
            "postgres": {
                "id": "YOUR_POSTGRES_CRED_ID",
                "name": "Postgres account"
            }
        }
    }
    wf['nodes'].append(sops_node)

# 4. Modify "Prep LLM Payload" to include SOPs
for node in wf['nodes']:
    if node['name'] == 'Prep LLM Payload':
        js = node['parameters']['jsCode']
        if 'const sops' not in js:
            new_code = js.replace('let monthlyContext = [];', 'let monthlyContext = [];\nlet sopsContext = [];\ntry {\n    const sops = $(\'Fetch SOPs\').all() || [];\n    sopsContext = sops.map(item => item.json);\n} catch(e) {}')
            new_code = new_code.replace('monthly_context: monthlyContext }', 'monthly_context: monthlyContext, sops: sopsContext }')
            node['parameters']['jsCode'] = new_code

# 5. Convert all Google Sheets nodes to Postgres placeholders to stop using Google Sheets
for node in wf['nodes']:
    if node['type'] == 'n8n-nodes-base.googleSheets':
        node['type'] = 'n8n-nodes-base.postgres'
        node['typeVersion'] = 2.2
        node['parameters'] = {
            "operation": "executeQuery",
            "query": f"-- Please configure this Postgres node to replace Google Sheets '{node['name']}'\n-- Example: INSERT INTO your_table (...) VALUES (...)",
            "options": {}
        }
        node['credentials'] = {
            "postgres": {
                "id": "YOUR_POSTGRES_CRED_ID",
                "name": "Postgres account"
            }
        }

with open(file_path, 'w', encoding='utf8') as f:
    json.dump(wf, f, indent=2)

print("Updated workflow JSON successfully.")
