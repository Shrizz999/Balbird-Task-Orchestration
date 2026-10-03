import sys
import os
from Stauff_Task_Orch.data.repository import GoogleSheetRepository

GSHEET_BASE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTHrHDX22vdQV7YQKrDOenwKBBenyG98ERPGBysBRRW-iKEuKBAryRb6hOQ_-zNuG2hq0Vd-KlBVN2o/pub"

repo = GoogleSheetRepository(GSHEET_BASE_URL)
tasks = repo.get_tasks()
found = [t for t in tasks if t.id == "TSK-260927-SHR-JB15"]
print(f"Found {len(found)} tasks with ID TSK-260927-SHR-JB15")
if found:
    print(found[0])
