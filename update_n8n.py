import json

file_path = "Stauff Task Orchestrator (Explicit Mapping)(1).json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for node in data["nodes"]:
    if node["name"] == "Format Daily Goals":
        node["parameters"]["jsCode"] = """const rawText = $input.first().json["Paste The JSON"]; 
const payload = JSON.parse(rawText);
const goalsData = payload.goals || {};
const splitItems = [];

for (const [name, detailsList] of Object.entries(goalsData)) {
  const items = Array.isArray(detailsList) ? detailsList : [detailsList];
  for (const details of items) {
    const dateStr = new Date().toISOString().slice(2, 10).replace(/-/g, '');
    const shortHash = Math.random().toString(36).substring(2, 6).toUpperCase();
    splitItems.push({
      json: {
        "Goal ID": `GOAL-${dateStr}-${name.substring(0,3).toUpperCase()}-${shortHash}`,
        "Time Frame": "Daily",
        "Week/Month": details.date || new Date().toLocaleDateString('en-GB'),
        "Assigned To": name,
        "Given By": "UI Input / Manager",
        "Goal": details.goal || details,
        "Deadline": details.deadline || "",
        "Priority": details.priority || "Normal",
        "Status": "Pending",
        "Reason": "",
        "Updated By": "n8n Automation",
        "Last Updated": new Date().toISOString()
      }
    });
  }
}
return splitItems;"""
    
    if node["name"] == "Format Monthly Goals":
        node["parameters"]["jsCode"] = """const rawText = $input.first().json["Paste The JSON"]; 
const payload = JSON.parse(rawText);
const goalsData = payload.goals || {};
const splitItems = [];

for (const [dept, details] of Object.entries(goalsData)) {
  const dateStr = new Date().toISOString().slice(2, 10).replace(/-/g, '');
  const shortHash = Math.random().toString(36).substring(2, 6).toUpperCase();
  splitItems.push({
    json: {
      "Goal ID": `GOAL-${dateStr}-${dept.substring(0,3).toUpperCase()}-${shortHash}`,
      "Time Frame": "Monthly",
      "Week/Month": details.month || new Date().toLocaleString('default', { month: 'long', year: 'numeric' }),
      "Assigned To": dept,
      "Given By": "UI Input / Manager",
      "Goal": details.goal || details,
      "Deadline": details.deadline || "End of Month",
      "Priority": details.priority || "Normal",
      "Status": "Pending",
      "Reason": "",
      "Updated By": "n8n Automation",
      "Last Updated": new Date().toISOString()
    }
  });
}
return splitItems;"""

    if node["type"] == "n8n-nodes-base.googleSheets" and "columns" in node["parameters"]:
        # Update the google sheets mappings to include Priority
        cols = node["parameters"]["columns"]
        if "value" in cols and isinstance(cols["value"], dict):
            cols["value"]["Priority"] = "={{ $json.Priority }}"
            
        if "schema" in cols and isinstance(cols["schema"], list):
            # Check if Priority exists
            has_priority = any(item.get("id") == "Priority" for item in cols["schema"])
            if not has_priority:
                cols["schema"].append({
                    "id": "Priority",
                    "displayName": "Priority",
                    "required": False,
                    "defaultMatch": False,
                    "display": True,
                    "type": "string",
                    "canBeUsedToMatch": True
                })

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Updated n8n JSON file.")
