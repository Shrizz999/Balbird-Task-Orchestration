import json
import uuid
import copy
import shutil

# Restore original
shutil.copyfile(r"c:\Users\User\Downloads\STO (2).json", "STO (1).json")

with open('STO (1).json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

nodes = wf['nodes']
connections = wf.get('connections', {})

# Find existing OpenRouter Chat Model and Basic LLM Chain
llm_chain = next(n for n in nodes if n['name'] == 'Basic LLM Chain')
openrouter = next(n for n in nodes if n['name'] == 'OpenRouter Chat Model')

# We'll create one LLM processing node for the structured input before Format Daily Goals
# We need a Code node to Prep the payload for this LLM
prep_node_id = str(uuid.uuid4())
prep_node = {
    "parameters": {
        "jsCode": """
const rawInput = $input.first().json['Paste The JSON'];
const inputType = $('On form submission').first().json['Select Input Type'];
let sopsContext = [];
try {
    const sops = $('Fetch SOPs').all() || [];
    sopsContext = sops.map(item => item.json);
} catch(e) {}

return [{ json: { raw_json: rawInput, sops: sopsContext, input_type: inputType } }];
"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-3500, -800],
    "id": prep_node_id,
    "name": "Prep Goals For LLM"
}

# New LLM Chain
new_llm_chain_id = str(uuid.uuid4())
new_llm_chain = copy.deepcopy(llm_chain)
new_llm_chain['id'] = new_llm_chain_id
new_llm_chain['name'] = "Goals LLM Chain"
new_llm_chain['position'] = [-3200, -800]
new_llm_chain['parameters']['text'] = '={{ $json.raw_json }}'
new_llm_chain['parameters']['messages']['messageValues'][0]['message'] = """=OUTPUT FORMAT:
You MUST output a valid JSON. 
You will be given a JSON with goals, e.g. {"goals": {"Shreyash": [{"goal": "...", "deadline": "..."}]}}.
Return the EXACT same JSON structure, but for every goal object, add a "checklist" property containing an array of strings representing 3 to maximum 4 high-level milestones.

CRITICAL HARD CONSTRAINTS (STRICTLY ENFORCED):
1. HARD LENGTH LIMIT — STRICTLY 3 TO MAX 4 ITEMS:
   - Every checklist MUST have a minimum of 3 and a MAXIMUM OF 4 items. NEVER exceed 4 items under any circumstances.
   - Any output with 5 or more items is strictly FORBIDDEN.
   - If a task is complex, you MUST merge/consolidate all intermediate actions into 3 or 4 major milestone phases.

2. MAJOR MILESTONES ONLY — NO FILLER OR COMMON SENSE:
   - Include ONLY core technical, operational, or deliverable stages (e.g., Phase 1: Planning/Design -> Phase 2: Execution/Machining -> Phase 3: Testing/QA -> Phase 4: Delivery/Sign-off).
   - NEVER create items for routine communications, administrative hygiene, or common sense (e.g., DO NOT write "Follow up", "Send email", "Call client", "Check inbox", "Attend meeting", "Review notes", "Open software").

3. CONCISE & ACTIONABLE:
   - Start each item with a decisive action verb (e.g., "Draft", "Fabricate", "Validate", "Approve").
   - Align with Company SOP procedures when relevant.

CONTEXT:
Company SOPs: {{ JSON.stringify($json.sops || []) }}

IMPORTANT:
- ONLY output the JSON. Do not output anything else.
- Keep each "checklist" strictly between 3 and 4 items maximum.
"""

# New OpenRouter
new_openrouter_id = str(uuid.uuid4())
new_openrouter = copy.deepcopy(openrouter)
new_openrouter['id'] = new_openrouter_id
new_openrouter['name'] = "OpenRouter For Goals"
new_openrouter['position'] = [-3200, -600]

# Code node to extract the JSON and pass it to Format Daily Goals
extract_node_id = str(uuid.uuid4())
extract_node = {
    "parameters": {
        "jsCode": """
const text = $input.first().json.text || "";
let cleanText = text;
const firstBrace = cleanText.indexOf('{');
const lastBrace = cleanText.lastIndexOf('}');
if (firstBrace !== -1 && lastBrace !== -1) { cleanText = cleanText.substring(firstBrace, lastBrace + 1); }

return [{ json: { "Paste The JSON": cleanText } }];
"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-2900, -800],
    "id": extract_node_id,
    "name": "Extract LLM Goals JSON"
}

nodes.extend([prep_node, new_llm_chain, new_openrouter, extract_node])

# Fix connections
# Route Input Router (0 and 1) -> Prep Goals For LLM
if 'Input Router' in connections:
    connections['Input Router']['main'][0] = [{"node": "Prep Goals For LLM", "type": "main", "index": 0}]
    connections['Input Router']['main'][1] = [{"node": "Prep Goals For LLM", "type": "main", "index": 0}]
    
connections['Prep Goals For LLM'] = {
    "main": [[{"node": "Goals LLM Chain", "type": "main", "index": 0}]]
}

connections['OpenRouter For Goals'] = {
    "ai_languageModel": [[{"node": "Goals LLM Chain", "type": "ai_languageModel", "index": 0}]]
}

connections['Goals LLM Chain'] = {
    "main": [[{"node": "Extract LLM Goals JSON", "type": "main", "index": 0}]]
}

# Switch node after Extract LLM Goals JSON
switch_node_id = str(uuid.uuid4())
switch_node = {
    "parameters": {
        "rules": {
            "values": [
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 3},
                        "conditions": [{"leftValue": "={{ $('Prep Goals For LLM').first().json.input_type }}", "rightValue": "Daily Goals", "operator": {"type": "string", "operation": "equals"}}],
                        "combinator": "and"
                    }
                },
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 3},
                        "conditions": [{"leftValue": "={{ $('Prep Goals For LLM').first().json.input_type }}", "rightValue": "Monthly Goals", "operator": {"type": "string", "operation": "equals"}}],
                        "combinator": "and"
                    }
                }
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.switch",
    "typeVersion": 3.4,
    "position": [-2600, -800],
    "id": switch_node_id,
    "name": "Goals Type Router"
}

nodes.append(switch_node)

connections['Extract LLM Goals JSON'] = {
    "main": [[{"node": "Goals Type Router", "type": "main", "index": 0}]]
}

connections['Goals Type Router'] = {
    "main": [
        [{"node": "Format Daily Goals", "type": "main", "index": 0}],
        [{"node": "Format Monthly Goals", "type": "main", "index": 0}]
    ]
}

# Format Daily/Monthly Goals code needs to use 'checklist'
for node in nodes:
    if node['name'] == 'Format Daily Goals':
        js = node['parameters']['jsCode']
        js = js.replace('"status": "Pending",', '"status": "Pending",\n        "checklist": details.checklist || [],')
        node['parameters']['jsCode'] = js
    if node['name'] == 'Format Monthly Goals':
        js = node['parameters']['jsCode']
        js = js.replace('"status": "Pending",', '"status": "Pending",\n        "checklist": details.checklist || [],')
        node['parameters']['jsCode'] = js

# Also update Upsert Monthly Goals to include checklist
for node in nodes:
    if node['name'] == 'Upsert Monthly Goals':
        q = node['parameters'].get('query', '')
        if 'checklist' not in q:
            q = q.replace('last_updated)', 'last_updated, checklist)')
            q = q.replace("now())", "now(), '{{ JSON.stringify($json.checklist) }}'::jsonb)")
            q = q.replace('last_updated = EXCLUDED.last_updated', 'last_updated = EXCLUDED.last_updated, checklist = EXCLUDED.checklist')
            node['parameters']['query'] = q
            
    if node['name'] == 'Upsert Tasks (Daily Goals)':
        q = node['parameters'].get('query', '')
        if 'checklist' not in q:
            q = q.replace('last_updated)', 'last_updated, checklist)')
            q = q.replace("now())", "now(), '{{ JSON.stringify($json.checklist) }}'::jsonb)")
            q = q.replace('last_updated = EXCLUDED.last_updated', 'last_updated = EXCLUDED.last_updated, checklist = EXCLUDED.checklist')
            node['parameters']['query'] = q

with open('STO (1).json', 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=2)

print("Restored STO (1).json from STO (2).json and successfully added LLMs between Input and Format Daily/Monthly Goals.")
