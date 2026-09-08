import os
import sys
import json
import sqlite3
import secrets
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DB_FILE = os.path.join(BASE_DIR, "invites.db")
OUTPUT_CSV = os.path.join(BASE_DIR, "generated_links.csv")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"base_url": "http://localhost:5000"}

def main():
    count = 350
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print("Invalid count specified. Using default: 350")

    cfg = load_config()
    base_url = cfg.get("base_url", "http://localhost:5000").rstrip("/")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            assigned_to TEXT,
            is_used INTEGER DEFAULT 0,
            used_at TEXT,
            ip_address TEXT,
            created_at TEXT
        )
    """)
    conn.commit()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    csv_rows = []

    print(f"Generating {count} unique one-time tokens...")

    for i in range(1, count + 1):
        token = secrets.token_urlsafe(12)
        assigned = f"Member #{i}"
        records.append((token, assigned, 0, None, None, now_str))
        full_url = f"{base_url}/join/{token}"
        csv_rows.append([i, assigned, full_url, "Active"])

    cursor.executemany("""
        INSERT INTO invites (token, assigned_to, is_used, used_at, ip_address, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    conn.close()

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Assigned To", "One-Time Link", "Status"])
        writer.writerows(csv_rows)

    print(f"SUCCESS: {count} links generated and inserted into database.")
    print(f"Exported CSV: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
