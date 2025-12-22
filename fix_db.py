import sqlite3

def fix_checklist_table():
    print("Connecting to database...")
    conn = sqlite3.connect('zion_ops.db')
    c = conn.cursor()

    # 1. AGGRESSIVE MOVE: Delete the old, broken table
    print("Dropping old table...")
    c.execute("DROP TABLE IF EXISTS checklist_logs")

    # 2. Create the NEW table with ALL required columns
    print("Creating new table...")
    c.execute('''
        CREATE TABLE checklist_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_name TEXT,
            task_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_logged TEXT,
            photo_proof TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("SUCCESS: Table 'checklist_logs' has been reset with correct columns!")

if __name__ == '__main__':
    fix_checklist_table()