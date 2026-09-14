"""
database.py
------------
Builds and manages the SQLite database for EcoSort AI.

Tables:
  items       -> the master waste-item catalog, loaded from the cleaned
                 1M1B dataset (data/Eco-Sort-Cleaned.csv)
  scan_logs   -> every time someone scans an item with the camera (or
                 searches for one), we log it here so the dashboard can
                 show real usage analytics
"""

import csv
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "eco_sort.db")
CSV_PATH = os.path.join(BASE_DIR, "..", "data", "Eco-Sort-Cleaned.csv")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(force=False):
    """Create tables and seed the items table from the CSV file.

    If force=True, drops existing tables first (useful during dev).
    Safe to call every time the server starts - it only seeds once.
    """
    conn = get_connection()
    cur = conn.cursor()

    if force:
        cur.execute("DROP TABLE IF EXISTS items")
        cur.execute("DROP TABLE IF EXISTS scan_logs")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            record_id INTEGER PRIMARY KEY,
            item TEXT NOT NULL,
            category TEXT,
            e_waste TEXT,
            hazard_level TEXT,
            recyclable TEXT,
            disposal_method TEXT,
            campus_location TEXT,
            instruction TEXT,
            expected_lifespan_years TEXT,
            replacement_period_years TEXT,
            life_status TEXT,
            reuse_possible TEXT,
            reuse_method TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,                 -- 'camera' or 'search'
            predicted_label TEXT,        -- raw label from the CV model
            confidence REAL,
            matched_item TEXT,
            matched_record_id INTEGER,
            timestamp TEXT DEFAULT (datetime('now'))
        )
        """
    )

    conn.commit()

    # Seed only if empty
    cur.execute("SELECT COUNT(*) AS c FROM items")
    count = cur.fetchone()["c"]

    if count == 0:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [
                (
                    int(row["record_id"]),
                    row["item"],
                    row["category"],
                    row["e_waste"],
                    row["hazard_level"],
                    row["recyclable"],
                    row["disposal_method"],
                    row["campus_location"],
                    row["instruction"],
                    row["expected_lifespan_years"],
                    row["replacement_period_years"],
                    row["life_status"],
                    row["reuse_possible"],
                    row["reuse_method"],
                )
                for row in reader
            ]
        cur.executemany(
            """
            INSERT INTO items (
                record_id, item, category, e_waste, hazard_level, recyclable,
                disposal_method, campus_location, instruction,
                expected_lifespan_years, replacement_period_years,
                life_status, reuse_possible, reuse_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        print(f"[database] Seeded {len(rows)} rows into items table.")
    else:
        print(f"[database] items table already has {count} rows, skipping seed.")

    conn.close()


if __name__ == "__main__":
    init_db(force=True)
    print("[database] Database initialised at", DB_PATH)
