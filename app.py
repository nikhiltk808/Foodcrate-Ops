from flask import Flask, redirect, url_for, session
from pathlib import Path
from datetime import datetime, timedelta
import os
import helpers as h
import database as db

# Import Blueprints
from routes_staff import staff_bp
from routes_api import api_bp
from routes_admin import admin_bp

app = Flask(__name__)

# SECRET: read from environment for safety; fallback only for quick local testing
app.secret_key = os.environ.get("ZION_SECRET_KEY", "change_this_local_only")

# --- CONFIG ---
UPLOAD_FOLDER = Path(__file__).parent / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)  # ensure string

# REGISTER BLUEPRINTS
app.register_blueprint(staff_bp)
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(admin_bp)

# Ensure DB tables exist at import (safe, non-destructive init)
try:
    db.init_db()
except Exception:
    # If init fails, leave it to update_db route to surface the error
    pass

# --- GLOBAL FILTERS ---
@app.template_filter('date_modify')
def date_modify(date_str, days):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return (dt + timedelta(days=int(days))).strftime('%Y-%m-%d')
    except:
        return date_str

@app.route('/')
def index():
    """Root route - redirect to appropriate dashboard based on user role."""
    if 'user_id' not in session:
        return redirect(url_for('admin.login'))
    
    # Redirect based on user role
    if session.get('user_role') == 'manager':
        return redirect(url_for('admin.home'))
    else:
        return redirect(url_for('staff.dashboard', route_user_id=session['user_id']))

# --- TEMPORARY DATABASE FIXER (should be protected in production) ---
@app.route('/update_db')
def update_db():
    try:
        db.init_db()
        return "<h1>✅ Database Updated Successfully!</h1><p>Tables created/updated.</p><a href='/'>Go to Dashboard</a>"
    except Exception as e:
        return f"<h1>❌ Error</h1><p>{str(e)}</p>"

@app.route('/fix_db_now')
def fix_db_now():
    import sqlite3
    conn = db.get_db()
    c = conn.cursor()
    try:
        # Try adding the missing column safely
        c.execute("ALTER TABLE todos ADD COLUMN due_date TEXT")
        conn.commit()
        return "<h1>✅ Success!</h1> <p>Database repaired. The 'due_date' column was added.</p> <a href='/'>Go to Dashboard</a>"
    except Exception as e:
        return f"<h1>⚠️ Info</h1> <p>{str(e)}</p> <p>(If it says 'duplicate column', that means it's already fixed!)</p> <a href='/'>Go to Dashboard</a>"

if __name__ == '__main__':
    # When run directly, allow overriding debug with env var FLASK_DEBUG=1
    debug_flag = bool(os.environ.get("FLASK_DEBUG", False))
    # Ensure DB is initialized when run locally
    db.init_db()
    app.run(host='0.0.0.0', port=5001, debug=debug_flag)