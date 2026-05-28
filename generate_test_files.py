# WorkTimeSync/generate_test_files.py
"""
Создаёт демонстрационные CSV и JSON для проверки импорта.
"""
import csv, json, os
from datetime import date

os.makedirs("static", exist_ok=True)

# Данные для импорта (несколько записей)
entries = [
    {"username": "ivan", "project_name": "WorkTime Sync", "hours": 4.5, "date": str(date.today())},
    {"username": "maria", "project_name": "WorkTime Sync", "hours": 3.0, "date": str(date.today())},
    {"username": "alex", "project_name": "WorkTime Sync", "hours": 6.0, "date": str(date.today())},
    {"username": "olga", "project_name": "WorkTime Sync", "hours": 7.5, "date": str(date.today())},
]

# CSV
csv_path = "static/sample_data.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["username", "project_name", "hours", "date"])
    writer.writeheader()
    writer.writerows(entries)
print(f"CSV создан: {csv_path}")

# JSON
json_path = "static/sample_data.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(entries, f, indent=2, ensure_ascii=False)
print(f"JSON создан: {json_path}")

