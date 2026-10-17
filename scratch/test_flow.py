import json

body = {
    'task_id': 'TSK-TEST-001',
    'update_text': 'I have thoroughly verified all bore dimensions and completed the formal inspection report. We also had lunch with John.',
    'task_description': 'Inspect pressure gauge parts',
    'current_checklist': [
        '[x] Receive raw materials from store',
        '[ ] Verify bore dimensions',
        '[ ] Complete inspection report',
        '[ ] Ship parts to customer'
    ],
    'status': 'Pending'
}

normalized = []
for item in body['current_checklist']:
    isChecked = item.strip().startswith('[x]')
    text = item.strip()
    if text.startswith('[x]') or text.startswith('[ ]'):
        text = text[3:].strip()
    normalized.append({'text': text, 'completed': isChecked})

print('Normalized checklist:', normalized)

llm_sample_output = """```json
{
  "checklist": [
    "[x] Receive raw materials from store",
    "[x] Verify bore dimensions",
    "[x] Complete inspection report",
    "[ ] Ship parts to customer"
  ],
  "all_completed": false,
  "newly_completed_steps": ["Verify bore dimensions", "Complete inspection report"],
  "still_pending_steps": ["Ship parts to customer"],
  "explanation": "Verified bore dimensions and completed inspection report as confirmed by the employee."
}
```"""

cleanText = llm_sample_output.strip()
firstBrace = cleanText.find('{')
lastBrace = cleanText.rfind('}')
cleanText = cleanText[firstBrace:lastBrace+1]
parsed = json.loads(cleanText)

print('Parsed checklist from LLM:', parsed['checklist'])
print('Newly completed:', parsed['newly_completed_steps'])
print('All completed?:', parsed['all_completed'])

completedCount = sum(1 for item in parsed['checklist'] if item.startswith('[x]'))
totalItems = len(parsed['checklist'])
allCompleted = (totalItems > 0 and completedCount == totalItems)
print(f'Count: {completedCount}/{totalItems}, All done: {allCompleted}')
