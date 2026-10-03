import re

with open('sheet.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Try to find the gid to name mapping
# In Google Sheets pubhtml, there's usually a block like `gid: "123", name: "Sheet1"`
matches = re.findall(r'\{id:"(\d+)",name:"([^"]+)"\}', html)
for match in matches:
    print(f"Name: {match[1]}, GID: {match[0]}")
