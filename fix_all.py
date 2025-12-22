import sqlite3

# Make sure this matches your actual DB name (check your 'Files' tab)
DB_NAME = 'zion_ops.db'

def fix_columns():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        print(f"🔧 Connecting to {DB_NAME}...")

        # List of columns to check/add
        columns_to_add = [
            ('checklist_logs', 'checklist_id', 'INTEGER'),
            ('checklist_logs', 'task_name', 'TEXT'),
            ('checklist_logs', 'photo_proof', 'TEXT'),
            ('checklists', 'trigger_time', 'TEXT'), # Just in case
        ]

        for table, col, dtype in columns_to_add:
            try:
                print(f"   Checking {table}.{col}...")
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {dtype}")
                print(f"   ✅ Added {col}")
            except sqlite3.OperationalError:
                print(f"   ℹ️ {col} already exists.")
            except Exception as e:
                print(f"   ❌ Error on {col}: {e}")

        conn.commit()
        conn.close()
        print("\n🎉 Database structure is now 100% correct.")

    except Exception as e:
        print(f"\n❌ CRITICAL DB ERROR: {e}")

if __name__ == "__main__":
    fix_columns()