import sqlite3
conn = sqlite3.connect('zion_ops.db')
c = conn.cursor()
try:
    c.execute("ALTER TABLE checklist_logs ADD COLUMN photo_proof TEXT")
    print("Column 'photo_proof' added successfully!")
except:
    print("Column might already exist.")
conn.commit()
conn.close()