import urllib.request
import re

url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTHrHDX22vdQV7YQKrDOenwKBBenyG98ERPGBysBRRW-iKEuKBAryRb6hOQ_-zNuG2hq0Vd-KlBVN2o/pubhtml"
html = urllib.request.urlopen(url).read().decode('utf-8')
matches = re.findall(r'\{id:"(.*?)",name:"(.*?)"\}', html)
for match in matches:
    print(f"Sheet: {match[1]}, GID: {match[0]}")
