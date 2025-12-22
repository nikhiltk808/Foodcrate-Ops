import sqlite3
import os

# Define path clearly
db_path = '/home/Nikhiltk808/zion_ops.db'

if not os.path.exists(db_path):
    print(f"❌ Error: Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("1. Installing 'Staff Notes' table...")
    cursor.execute("CREATE TABLE IF NOT EXISTS staff_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, note TEXT, author TEXT, timestamp DATETIME)")

    print("2. Verifying 'News Updates' table...")
    cursor.execute("CREATE TABLE IF NOT EXISTS news_updates (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, created_at DATETIME, expires_at DATETIME)")

    conn.commit()
    conn.close()
    print("✅ SUCCESS! Admin features installed.")