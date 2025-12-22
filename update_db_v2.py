import sqlite3

def add_checklist_table():
    conn = sqlite3.connect('zion_ops.db')
    c = conn.cursor()

    # Create table for checklist logs
    # Stores: Who did it, What task, Type (Opening/Closing), and When
    c.execute('''
        CREATE TABLE IF NOT EXISTS checklist_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_name TEXT,
            task_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_logged TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("Database updated! 'checklist_logs' table created.")

if __name__ == '__main__':
    add_checklist_table()