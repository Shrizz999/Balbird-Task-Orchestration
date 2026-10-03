import json

file_path = "Stauff Task Orchestrator (Explicit Mapping)(1).json"
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for node in data["nodes"]:
    if node["name"] == "Extract & Map Tasks":
        node["parameters"]["jsCode"] = """const rawText = $input.first().json["Paste The JSON"]; 
const payload = JSON.parse(rawText);

const uiUpdates = payload.individual_updates || []; // Now a list of task dicts
const tasks = [];

for (const update of uiUpdates) {
    tasks.push(update); // Simply push the full task dict we sent from the UI
}

// Map tasks to individual Google Sheets updates
const splitItems = tasks.map(task => {
  const dateStr = new Date().toISOString().slice(2, 10).replace(/-/g, '');
  const safeName = (task["Assigned To"] || 'UNK').substring(0, 3).toUpperCase();
  const shortHash = Math.random().toString(36).substring(2, 6).toUpperCase();
  
  // If we provided a Task ID (from the UI), use it. Otherwise (e.g. from LLM or new), generate one.
  const taskId = task["Task ID"] ? task["Task ID"] : `TSK-${dateStr}-${safeName}-${shortHash}`;
  
  return {
    json: {
      "Task ID": taskId,
      "Date": task["Date"] || new Date().toLocaleDateString('en-GB'),
      "Task Description": task["Task Description"] || task["goal"] || task["Task_Description"] || "",
      "Assigned To": task["Assigned To"] || task["assigned_to"] || "",
      "Assigned By": task["Assigned By"] || task["assigned_by"] || "UI Input",
      "Deadline": task["Deadline"] || task["deadline"] || "",
      "Priority": task["Priority"] || task["priority"] || "Normal",
      "Status": task["Status"] || task["status"] || "Pending",
      "Reason": task["Reason"] || task["reason"] || "",
      "Source": task["Source"] || task["source"] || "UI Input",
      "Updated By": task["Task ID"] ? "UI Input" : "n8n Automation", // Differentiate update vs new
      "Last Updated": new Date().toISOString()
    }
  };
});

return splitItems;"""

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print("Updated Extract & Map Tasks code.")
