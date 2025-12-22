import sqlite3
import os

# Connect to database
db_path = "zion_ops.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🧹 STARTING CLEANUP...")

# 1. Count rows before deleting (just to see how bad it was)
try:
    count_att = cursor.execute("SELECT count(*) FROM attendance").fetchone()[0]
    count_logs = cursor.execute("SELECT count(*) FROM checklist_logs").fetchone()[0]
    count_roster = cursor.execute("SELECT count(*) FROM roster").fetchone()[0]
    print(f"⚠️ Found {count_att} attendance logs.")
    print(f"⚠️ Found {count_logs} checklist logs.")
    print(f"⚠️ Found {count_roster} roster entries.")
except:
    print("Could not count rows (tables might be missing).")

# 2. DELETE ALL OPERATIONAL DATA (Keep Users & Settings)
# We do NOT delete 'users', 'checklists', 'events' so your setup stays.
# We ONLY delete the history that is causing the crash.
cursor.execute("DELETE FROM attendance")
cursor.execute("DELETE FROM checklist_logs")
cursor.execute("DELETE FROM roster")
cursor.execute("DELETE FROM leave_requests")

# 3. Vacuum (Shrink the file size and repair structure)
cursor.execute("VACUUM")

conn.commit()
conn.close()

print("✅ SUCCESS! Database history has been wiped.")
print("🚀 You can now restart 'app.py' and login without crashing.")