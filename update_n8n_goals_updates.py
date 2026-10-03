import json
import os

input_file = "Stauff_Task_Orchestrator_V2.json"
if not os.path.exists(input_file):
    input_file = "Stauff Task Orchestrator (Explicit Mapping)(1).json"

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# 1. Update Input Router to have a new rule for "Live Updates Goals"
for node in data["nodes"]:
    if node["name"] == "Input Router" and node["type"] == "n8n-nodes-base.switch":
        rules = node["parameters"]["rules"]["values"]
        exists = any(r.get("conditions", {}).get("conditions", [{}])[0].get("rightValue") == "Live Updates Goals" for r in rules)
        if not exists:
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
                            "rightValue": "Live Updates Goals",
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

# 2. Add Format Live Updates Goals node
format_node = {
    "parameters": {
        "jsCode": """const rawText = $input.first().json["Paste The JSON"]; 
const payload = JSON.parse(rawText);

const uiUpdates = payload.individual_updates || []; 
const splitItems = [];

for (const task of uiUpdates) {
  splitItems.push({
    json: {
      "Goal ID": task["Task ID"],
      "Assigned To": task["Assigned To"],
      "Task Description": task["Task Description"],
      "Deadline": task["Deadline"],
      "Status": task["Status"],
      "Reason": task["Reason"] || "",
      "Updated By": "UI Input", 
      "Last Updated": new Date().toISOString()
    }
  });
}

return splitItems;"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-380, 800],
    "id": "format-live-updates-goals-node",
    "name": "Format Live Updates Goals"
}

# 3. Add Upsert Goals from Updates node
upsert_goals_node = {
    "parameters": {
        "operation": "appendOrUpdate",
        "documentId": {
            "__rl": True,
            "value": "1-FHIzz0ACiGN-vwd0ABITj8FVei7pwEYiJIFDGBqEf4",
            "mode": "list",
            "cachedResultName": "Copy of BalPigeon"
        },
        "sheetName": {
            "__rl": True,
            "value": 1837353468,
            "mode": "list",
            "cachedResultName": "Goals"
        },
        "columns": {
            "mappingMode": "defineBelow",
            "value": {
                "Goal ID": "={{ $json['Goal ID'] }}",
                "Assigned To": "={{ $json['Assigned To'] }}",
                "Goal": "={{ $json['Task Description'] }}",
                "Deadline": "={{ $json.Deadline }}",
                "Status": "={{ $json.Status }}",
                "Reason": "={{ $json.Reason }}",
                "Updated By": "={{ $json['Updated By'] }}",
                "Last Updated": "={{ $json['Last Updated'] }}"
            },
            "matchingColumns": ["Goal ID"]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.googleSheets",
    "typeVersion": 4.7,
    "position": [-100, 800],
    "id": "upsert-goals-from-updates-node-v3",
    "name": "Upsert Goals from Updates",
    "credentials": {
        "googleSheetsOAuth2Api": {
            "id": "e1MbcUzueWdnMKx5",
            "name": "Google Sheets account"
        }
    }
}

# Add nodes to graph
data["nodes"] = [n for n in data["nodes"] if n["name"] not in ["Format Live Updates Goals", "Upsert Goals from Updates"]]
data["nodes"].append(format_node)
data["nodes"].append(upsert_goals_node)

# 4. Connections
if "Input Router" in data["connections"]:
    main_conn = data["connections"]["Input Router"]["main"]
    while len(main_conn) < len(rules):
        main_conn.append([])
    
    last_idx = len(rules) - 1
    main_conn[last_idx] = [{"node": "Format Live Updates Goals", "type": "main", "index": 0}]

data["connections"]["Format Live Updates Goals"] = {
    "main": [
        [{"node": "Upsert Goals from Updates", "type": "main", "index": 0}]
    ]
}

output_path = "Stauff_Task_Orchestrator_V3.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Generated {output_path}. Please import this into n8n.")
