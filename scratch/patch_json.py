import json

new_parsing = """const text = $input.first().json.text || "";
let cleanText = text;

// Find the first { and last } to robustly extract the JSON
const firstBrace = cleanText.indexOf('{');
const lastBrace = cleanText.lastIndexOf('}');
if (firstBrace !== -1 && lastBrace !== -1) {
    cleanText = cleanText.substring(firstBrace, lastBrace + 1);
}

let parsed = { Tasks: [], Reports: [] };
try { 
    parsed = JSON.parse(cleanText); 
} catch (e) { 
    console.log("LLM Parse Error:", e); 
}"""

with open('Stauff_Task_Orchestrator_V2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

count = 0
for node in data['nodes']:
    if node['name'] in ['Extract & Map Tasks', 'Extract Reports']:
        js_code = node['parameters'].get('jsCode', '')
        
        lines = js_code.split('\n')
        if lines and lines[0].startswith('const text ='):
            # Replace lines 0 to 6 with new_parsing
            new_code = new_parsing + '\n' + '\n'.join(lines[7:])
            node['parameters']['jsCode'] = new_code
            count += 1

if count > 0:
    with open('Stauff_Task_Orchestrator_V2.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Successfully patched {count} nodes.")
else:
    print("No nodes were patched.")
