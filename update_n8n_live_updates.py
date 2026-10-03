import json

file_path = r"C:\Users\User\Downloads\Stauff Task Orchestrator.json"
output_path = r"c:\Programming\Stauff_TO_v2\Stauff_Task_Orchestrator_V2.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 1. Update Switch node
for node in data["nodes"]:
    if node["name"] == "Input Router" and node["type"] == "n8n-nodes-base.switch":
        rules = node["parameters"]["rules"]["values"]
        # Check if 4th rule exists
        if len(rules) < 4:
            rules.append({
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 3
                    },
                    "conditions": [
                        {
                            "leftValue": "={{ $json['Select Input Type'] }}",
                            "rightValue": "Live Updates",
                            "operator": {
                                "type": "string",
                                "operation": "equals"
                            }
                        }
                    ],
                    "combinator": "and"
                }
            })
        break

# 2. Add or update "Format Live Updates" node
format_node = {
    "parameters": {
        "jsCode": """const rawText = $input.first().json["Paste The JSON"]; 
const payload = JSON.parse(rawText);

const uiUpdates = payload.individual_updates || []; 
const tasks = [];

for (const update of uiUpdates) {
    tasks.push(update); 
}

const splitItems = tasks.map(task => {
  return {
    json: {
      "Goal ID": task["Task ID"],
      "Task ID": task["Task ID"],
      "Date": task["Date"],
      "Task Description": task["Task Description"],
      "Goal": task["Task Description"],
      "Assigned To": task["Assigned To"],
      "Assigned By": task["Assigned By"],
      "Given By": task["Assigned By"],
      "Deadline": task["Deadline"],
      "Priority": task["Priority"] || "Normal",
      "Status": task["Status"],
      "Reason": task["Reason"] || "",
      "Source": task["Source"],
      "Updated By": "UI Input", 
      "Last Updated": new Date().toISOString()
    }
  };
});

return splitItems;"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [
        -384,
        600
    ],
    "id": "format-live-updates-node",
    "name": "Format Live Updates"
}

# Replace if existing or append
data["nodes"] = [n for n in data["nodes"] if n["name"] != "Format Live Updates"]
data["nodes"].append(format_node)

# 3. Add "Upsert Goals from Updates" node
upsert_goals_node = {
    "parameters": {
        "operation": "appendOrUpdate",
        "documentId": {
            "__rl": True,
            "value": "1-FHIzz0ACiGN-vwd0ABITj8FVei7pwEYiJIFDGBqEf4",
            "mode": "list",
            "cachedResultName": "Copy of BalPigeon",
            "cachedResultUrl": "https://docs.google.com/spreadsheets/d/1-FHIzz0ACiGN-vwd0ABITj8FVei7pwEYiJIFDGBqEf4/edit?usp=drivesdk"
        },
        "sheetName": {
            "__rl": True,
            "value": 1837353468,
            "mode": "list",
            "cachedResultName": "Goals",
            "cachedResultUrl": "https://docs.google.com/spreadsheets/d/1-FHIzz0ACiGN-vwd0ABITj8FVei7pwEYiJIFDGBqEf4/edit#gid=1837353468"
        },
        "columns": {
            "mappingMode": "defineBelow",
            "value": {
                "Goal ID": "={{ $json['Task ID'] }}",
                "Assigned To": "={{ $json['Assigned To'] }}",
                "Goal": "={{ $json['Task Description'] }}",
                "Deadline": "={{ $json.Deadline }}",
                "Status": "={{ $json.Status }}",
                "Reason": "={{ $json.Reason }}",
                "Updated By": "={{ $json['Updated By'] }}",
                "Last Updated": "={{ $json['Last Updated'] }}"
            },
            "matchingColumns": [
                "Goal ID"
            ],
            "schema": [
                {
                    "id": "Goal ID",
                    "displayName": "Goal ID",
                    "required": False,
                    "defaultMatch": False,
                    "display": True,
                    "type": "string",
                    "canBeUsedToMatch": True
                },
                {
                    "id": "Assigned To",
                    "displayName": "Assigned To",
                    "required": False,
                    "defaultMatch": False,
                    "display": True,
                    "type": "string",
                    "canBeUsedToMatch": True
                },
                {
                    "id": "Goal",
                    "displayName": "Goal",
                    "required": False,
                    "defaultMatch": False,
                    "display": True,
                    "type": "string",
                    "canBeUsedToMatch": True
                },
                {
                    "id": "Deadline",
                    "displayName": "Deadline",
                    "required": False,
                    "defaultMatch": False,
                    "display": True,
                    "type": "string",
                    "canBeUsedToMatch": True
                },
                {
                    "id": "Status",
                    "displayName": "Status",
                    "required": False,
                    "defaultMatch": False,
                    "display": True,
                    "type": "string",
                    "canBeUsedToMatch": True
                },
                {
                    "id": "Reason",
                    "displayName": "Reason",
                    "required": False,
                    "defaultMatch": False,
                    "display": True,
                    "type": "string",
                    "canBeUsedToMatch": True
                },
                {
                    "id": "Updated By",
                    "displayName": "Updated By",
                    "required": False,
                    "defaultMatch": False,
                    "display": True,
                    "type": "string",
                    "canBeUsedToMatch": True
                },
                {
                    "id": "Last Updated",
                    "displayName": "Last Updated",
                    "required": False,
                    "defaultMatch": False,
                    "display": True,
                    "type": "string",
                    "canBeUsedToMatch": True
                }
            ],
            "attemptToConvertTypes": False,
            "convertFieldsToString": False
        },
        "options": {}
    },
    "type": "n8n-nodes-base.googleSheets",
    "typeVersion": 4.7,
    "position": [
        -80,
        750
    ],
    "id": "upsert-goals-from-updates-node",
    "name": "Upsert Goals from Updates",
    "credentials": {
        "googleSheetsOAuth2Api": {
            "id": "e1MbcUzueWdnMKx5",
            "name": "Google Sheets account"
        }
    }
}

data["nodes"] = [n for n in data["nodes"] if n["name"] != "Upsert Goals from Updates"]
data["nodes"].append(upsert_goals_node)

# 4. Connections
# Input Router -> Format Live Updates
if "Input Router" in data["connections"]:
    main_conn = data["connections"]["Input Router"]["main"]
    if len(main_conn) < 4:
        main_conn.append([{"node": "Format Live Updates", "type": "main", "index": 0}])

# Format Live Updates -> Task Router AND Upsert Goals from Updates
data["connections"]["Format Live Updates"] = {
    "main": [
        [
            {"node": "Task Router", "type": "main", "index": 0},
            {"node": "Upsert Goals from Updates", "type": "main", "index": 0}
        ]
    ]
}

# 5. Revert Extract & Map Tasks
for node in data["nodes"]:
    if node["name"] == "Extract & Map Tasks":
        node["parameters"]["jsCode"] = """const text = $input.first().json.text;
const cleanText = text.replace(/```json/gi, "").replace(/```/gi, "").trim();
let parsed = { Tasks: [], Reports: [] };

try { parsed = JSON.parse(cleanText); } 
catch (e) { console.log("LLM Parse Error"); }

const tasks = parsed.Tasks || [];

return tasks.map(t => {
    const safeName = (t.Assigned_To || "UNK").substring(0,3).toUpperCase();
    const dateStr = new Date().toISOString().slice(2, 10).replace(/-/g, '');
    const shortHash = Math.random().toString(36).substring(2, 6).toUpperCase();
    
    return { 
      json: {
        "Task ID": `TSK-${dateStr}-${safeName}-${shortHash}`,
        "Date": new Date().toLocaleDateString('en-GB'),
        "Task Description": t.Task_Description || "-",
        "Assigned To": t.Assigned_To || "-",
        "Assigned By": t.Assigned_By || "-",
        "Deadline": t.Deadline || "",
        "Status": t.Status || "Pending",
        "Reason": t.Reason || "",
        "Source": t.Source || "Meeting Transcript",
        "Updated By": "n8n Automation",
        "Last Updated": new Date().toISOString()
      }
    };
});"""
        break

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Successfully updated n8n JSON and saved to", output_path)
