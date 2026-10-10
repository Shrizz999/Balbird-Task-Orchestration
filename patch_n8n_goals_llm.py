import json
import uuid
import copy

with open('STO (1).json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

nodes = wf['nodes']
connections = wf.get('connections', {})

# We will modify "Prep LLM Payload" to include inputType.
for node in nodes:
    if node['name'] == 'Prep LLM Payload':
        jsCode = node['parameters']['jsCode']
        if 'const inputType' not in jsCode:
            jsCode = jsCode.replace('const rawInput = $(\'On form submission\').first().json[\'Paste The JSON\'];',
                                  'const rawInput = $(\'On form submission\').first().json[\'Paste The JSON\'];\nconst inputType = $(\'On form submission\').first().json[\'Select Input Type\'];')
            
            # Change how finalTranscript is parsed if inputType is Daily or Monthly Goals
            new_logic = """
try {
    const parsedData = JSON.parse(rawInput);
    if (inputType === 'Daily Goals' || inputType === 'Monthly Goals') {
        finalTranscript = `Please process these ${inputType} and extract them as ${inputType === 'Daily Goals' ? 'Tasks' : 'Monthly_Goals'}. Include a detailed AI-generated checklist based on SOPs for each task.\\n`;
        const goals = parsedData.goals || {};
        for (const [assignee, tasksList] of Object.entries(goals)) {
            const arr = Array.isArray(tasksList) ? tasksList : [tasksList];
            for (const t of arr) {
                finalTranscript += `Assignee/Dept: ${assignee}. Goal/Task: ${t.goal || t.task || t}. Deadline: ${t.deadline || ''}. Priority: ${t.priority || 'Normal'}. Source: ${inputType}.\\n`;
            }
        }
    } else {
        finalTranscript = parsedData.transcript || "";
        individualUpdates = parsedData.individual_updates || {};
    }
} catch (e) {
    finalTranscript = rawInput;
}
"""
            jsCode = jsCode.replace('try {\n    const parsedData = JSON.parse(rawInput);\n    finalTranscript = parsedData.transcript || "";\n    individualUpdates = parsedData.individual_updates || {};\n} catch (e) {\n    finalTranscript = rawInput;\n}', new_logic.strip())
            
            # Output inputType as well
            jsCode = jsCode.replace('monthly_context: monthlyContext, sops: sopsContext }', 'monthly_context: monthlyContext, sops: sopsContext, input_type: inputType }')
            node['parameters']['jsCode'] = jsCode

# Now modify Basic LLM Chain to support Monthly_Goals output
for node in nodes:
    if node['name'] == 'Basic LLM Chain':
        msgs = node['parameters']['messages']['messageValues']
        for msg in msgs:
            if msg['type'] == 'HumanMessagePromptTemplate':
                old_text = msg['message']
                if 'Monthly_Goals' not in old_text:
                    new_text = old_text.replace('"Tasks" and "Reports"', '"Tasks", "Monthly_Goals", and "Reports"')
                    monthly_schema = """
"Monthly_Goals" Schema (Only output if the input contains Monthly Goals):
{
  "Goal_ID": "[Leave blank]",
  "Checklist": ["Step 1", "Step 2", "..."], // AI Generated stepwise task checklist
  "Goal": "Monthly goal description",
  "Assigned_To": "[Name/Dept]",
  "Deadline": "[Extracted deadline in DD/MM/YYYY format or End of Month]",
  "Priority": "Normal"
}
"""
                    new_text = new_text.replace('"Reports" Schema:', monthly_schema + '\n"Reports" Schema:')
                    msg['message'] = new_text

# Modify Extract & Map Tasks to parse Monthly_Goals and output to index 0 or 1
for node in nodes:
    if node['name'] == 'Extract & Map Tasks':
        jsCode = """
const text = $input.first().json.text || "";
const inputType = $input.first().json.input_type || "";
let cleanText = text;
const firstBrace = cleanText.indexOf('{');
const lastBrace = cleanText.lastIndexOf('}');
if (firstBrace !== -1 && lastBrace !== -1) { cleanText = cleanText.substring(firstBrace, lastBrace + 1); }

let parsed = { Tasks: [], Reports: [], Monthly_Goals: [] };
try { parsed = JSON.parse(cleanText); } catch (e) { console.log("LLM Parse Error:", e); }

const tasks = parsed.Tasks || [];
const monthly = parsed.Monthly_Goals || [];

const DEPT_MAP = { "Ganesh": "PO department", "Shreyash": "SO department", "Shruti": "Sales Department", "Vaishnavi": "Logistics Department" };

let output = [];

if (inputType === 'Monthly Goals' || monthly.length > 0) {
    // Process Monthly Goals
    output = monthly.map(t => {
        const dateStr = new Date().toISOString().slice(2, 10).replace(/-/g, '');
        const shortHash = Math.random().toString(36).substring(2, 6).toUpperCase();
        const goalId = `GOAL-${dateStr}-${(t.Assigned_To||"UNK").substring(0,3).toUpperCase()}-${shortHash}`;
        return {
            json: {
                "goal_id": goalId,
                "time_frame": "Monthly",
                "week_month": new Date().toLocaleString('default', { month: 'long', year: 'numeric' }),
                "assigned_to": t.Assigned_To || "-",
                "given_by": "Manager",
                "goal": t.Goal || t.Task_Description || "-",
                "deadline": t.Deadline || "End of Month",
                "status": "Pending",
                "reason": "",
                "updated_by": "n8n Automation",
                "last_updated": new Date().toISOString(),
                "checklist": t.Checklist || []
            }
        };
    });
} else {
    // Process Tasks
    output = tasks.map(t => {
        const safeName = (t.Assigned_To || "UNK").substring(0,3).toUpperCase();
        const dateStr = new Date().toISOString().slice(2, 10).replace(/-/g, '');
        const shortHash = Math.random().toString(36).substring(2, 6).toUpperCase();
        const taskId = (t.Task_ID && t.Task_ID.trim() !== "") ? t.Task_ID : `TSK-${dateStr}-${safeName}-${shortHash}`;
        const dept = DEPT_MAP[t.Assigned_To] || "Other";
        return { 
            json: { 
                "task_id": taskId, 
                "date": new Date().toLocaleDateString('en-GB'), 
                "description": t.Task_Description || t.Goal || "-", 
                "assigned_to": t.Assigned_To || "-", 
                "assigned_by": t.Assigned_By || "Manager", 
                "department": dept, 
                "deadline": t.Deadline || "", 
                "priority": t.Priority || "Normal", 
                "status": t.Status || "Pending", 
                "reason": t.Reason || "", 
                "source": t.Source || "Meeting Transcript", 
                "updated_by": "n8n Automation", 
                "last_updated": new Date().toISOString(), 
                "checklist": t.Checklist || [] 
            } 
        };
    });
}

return output;
"""
        node['parameters']['jsCode'] = jsCode.strip()

# Now update the Input Router so that Daily Goals and Monthly Goals go to Fetch All Tasks Context
# instead of their own formatter nodes.
for node in nodes:
    if node['name'] == 'Input Router':
        # Route 0 (Daily Goals), 1 (Monthly Goals), 2 (Daily Transcript)
        pass # The router just outputs them.

if 'Input Router' in connections:
    # Reroute index 0 (Daily Goals) and index 1 (Monthly Goals) to 'Fetch All Tasks Context'
    fetch_context = [{"node": "Fetch All Tasks Context", "type": "main", "index": 0}]
    connections['Input Router']['main'][0] = fetch_context
    connections['Input Router']['main'][1] = fetch_context

# Now, we need a Switch/Router after 'Extract & Map Tasks'
# We will change Extract & Map Tasks to connect to a new Switch Node.
switch_node_id = str(uuid.uuid4())
switch_node = {
    "parameters": {
        "rules": {
            "values": [
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 3},
                        "conditions": [{"leftValue": "={{ $json.time_frame }}", "rightValue": "Monthly", "operator": {"type": "string", "operation": "equals"}}],
                        "combinator": "and"
                    }
                }
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.switch",
    "typeVersion": 3.4,
    "position": [-1900, -336],
    "id": switch_node_id,
    "name": "Goal/Task Router"
}

if not any(n['name'] == 'Goal/Task Router' for n in nodes):
    nodes.append(switch_node)

if 'Extract & Map Tasks' in connections:
    connections['Extract & Map Tasks']['main'] = [[{"node": "Goal/Task Router", "type": "main", "index": 0}]]

connections['Goal/Task Router'] = {
    "main": [
        [{"node": "Upsert Monthly Goals", "type": "main", "index": 0}], # index 0 matches condition (Monthly)
        [{"node": "Upsert Tasks (Transcript)", "type": "main", "index": 0}] # index 1 is fallback (Tasks)
    ]
}

# Ensure Upsert Monthly Goals maps the new checklist
for node in nodes:
    if node['name'] == 'Upsert Monthly Goals' and node['type'] == 'n8n-nodes-base.postgres':
        query = node['parameters'].get('query', '')
        if 'checklist' not in query:
            # Modify the INSERT query to include checklist
            if 'last_updated)' in query:
                query = query.replace('last_updated)', 'last_updated, checklist)')
                query = query.replace("now())", "now(), '{{ JSON.stringify($json.checklist) }}'::jsonb)")
                query = query.replace('last_updated = EXCLUDED.last_updated', 'last_updated = EXCLUDED.last_updated, checklist = EXCLUDED.checklist')
            node['parameters']['query'] = query


with open('STO (1).json', 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=2)

print("N8n workflow successfully patched!")
