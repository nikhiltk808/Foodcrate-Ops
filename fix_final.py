import sqlite3

DB_NAME = 'zion_ops.db'

def fix_data_column():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        print(f"🔧 Connecting to {DB_NAME}...")

        # Explicitly add the missing 'data' column
        try:
            print("   Checking for 'data' column...")
            c.execute("ALTER TABLE checklist_logs ADD COLUMN data TEXT")
            print("   ✅ Success: Added 'data' column.")
        except sqlite3.OperationalError:
            print("   ℹ️ 'data' column already exists.")

        conn.commit()
        conn.close()
        print("\n🎉 Repair Complete. The submission should work now.")

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    fix_data_column()