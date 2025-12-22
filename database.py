import sqlite3
from pathlib import Path
from datetime import datetime
import os

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "zion_ops.db"

def get_db():
    """Establishes a connection to the database safely for WSGI multi-threading."""
    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys and sensible pragmas
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")  # WAL helps concurrent readers/writers
    except Exception:
        pass
    return conn

def add_column_if_not_exists(conn, table, column, col_type):
    """Add column only if it does not exist (safe migration helper)."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [r["name"] for r in cur.fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()

def init_db():
    """MASTER INITIALIZATION: creates tables if not exists and performs safe migrations."""
    with get_db() as conn:
        c = conn.cursor()

        # 1. Users & Auth
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                pin TEXT,
                role TEXT,
                department TEXT
            )
        """)

        # 2. Operations
        c.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                timestamp DATETIME,
                lat TEXT,
                lon TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS checklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                tasks TEXT,
                assigned_to TEXT,
                frequency TEXT,
                trigger_time TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS checklist_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                checklist_id INTEGER,
                task_name TEXT,
                task_type TEXT,
                photo_proof TEXT,
                data TEXT,
                timestamp DATETIME,
                edit_history TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                checklist_id INTEGER,
                request_type TEXT,
                status TEXT,
                timestamp TEXT
            )
        """)

        # 3. Communication
        c.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                message TEXT,
                meta_info TEXT,
                is_active INTEGER,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS acknowledgments (
                user_id INTEGER,
                announcement_id INTEGER,
                timestamp TEXT,
                PRIMARY KEY(user_id, announcement_id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                office_lat TEXT,
                office_lon TEXT,
                radius INTEGER
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS duty_instructions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                event_date TEXT,
                reporting_time TEXT,
                content TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)

        # 4. PERSONAL TO-DO LIST (safe migration: add due_date if missing)
        # Create table if missing
        c.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task TEXT,
                status TEXT,
                created_at TEXT
            )
        """)
        # Add due_date column only if not present
        add_column_if_not_exists(conn, "todos", "due_date", "TEXT")

        # Seed Admin user if not present
        try:
            row = conn.execute("SELECT COUNT(1) as c FROM users WHERE name = ?", ("Admin",)).fetchone()
            if row is None or row["c"] == 0:
                conn.execute("INSERT INTO users (name, pin, role, department) VALUES (?, ?, ?, ?)",
                             ("Admin", "1234", "manager", "Admin"))
        except Exception:
            # In case of any race condition or uniqueness error, ignore
            pass

        conn.commit()

def get_system_config():
    """Fetches GPS settings or returns defaults."""
    with get_db() as conn:
        try:
            row = conn.execute("SELECT * FROM system_settings LIMIT 1").fetchone()
            if row:
                return {'lat': float(row['office_lat']), 'lon': float(row['office_lon']), 'rad': int(row['radius'])}
        except Exception:
            pass
    return {'lat': 12.9716, 'lon': 77.5946, 'rad': 500}  # Defaults