import os
import csv

files = [
    "Copy of BalPigeon - Goals.csv",
    "Copy of BalPigeon - Ganesh.csv",
    "Copy of BalPigeon - Shreyash.csv",
    "Copy of BalPigeon - Shruti.csv",
    "Copy of BalPigeon - Vaishnavi.csv"
]

for filename in files:
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if lines:
            header = lines[0].strip()
            if "Priority" not in header:
                lines[0] = header + ",Priority\n"
                for i in range(1, len(lines)):
                    lines[i] = lines[i].strip() + ",Normal\n"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"Updated {filename}")
            else:
                print(f"{filename} already has Priority")
