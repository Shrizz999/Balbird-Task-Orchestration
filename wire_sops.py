import json

file_path = 'c:/Programming/Stauff_TO_v2/Stauff - Extension Requests.json'
with open(file_path, 'r', encoding='utf8') as f:
    wf = json.load(f)

# Connect 'Fetch Monthly Context' to 'Fetch SOPs' instead of 'Prep LLM Payload'
wf['connections']['Fetch Monthly Context'] = {
    "main": [
        [
            {
                "node": "Fetch SOPs",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

# Connect 'Fetch SOPs' to 'Prep LLM Payload'
wf['connections']['Fetch SOPs'] = {
    "main": [
        [
            {
                "node": "Prep LLM Payload",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

with open(file_path, 'w', encoding='utf8') as f:
    json.dump(wf, f, indent=2)

print("Wired Fetch SOPs node into the workflow.")
