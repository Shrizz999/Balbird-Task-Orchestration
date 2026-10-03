import urllib.request
url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTHrHDX22vdQV7YQKrDOenwKBBenyG98ERPGBysBRRW-iKEuKBAryRb6hOQ_-zNuG2hq0Vd-KlBVN2o/pub?output=csv&gid=130949039"
try:
    data = urllib.request.urlopen(url).read().decode('utf-8')
    print(data[:500])
except Exception as e:
    print(f"Error: {e}")
