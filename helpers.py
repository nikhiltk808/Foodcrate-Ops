from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from database import get_db
from functools import wraps
from flask import session, redirect, url_for

# --- CONSTANTS (single source) ---
IST_OFFSET = timedelta(hours=5, minutes=30)

# --- THEME CONFIG ---
THEME = {
    'primary': '#4361ee', 'secondary': '#3f37c9', 'success': '#10b981',
    'warning': '#f59e0b', 'bg': '#f8fafc', 'card': '#ffffff', 'text': '#1e293b'
}

# --- AUTH DECORATOR ---
def require_roles(*roles):
    """Decorator to enforce role-based access for routes.
    Example: @require_roles('manager') or @require_roles('manager', 'staff')
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('admin.login'))
            if session.get('user_role') not in roles:
                return "Unauthorized", 403
            return f(*args, **kwargs)
        return wrapped
    return decorator

# --- GPS / MATH HELPERS ---
def haversine(lon1, lat1, lon2, lat2):
    """Calculates GPS distance in meters."""
    try:
        lon1, lat1, lon2, lat2 = map(float, [lon1, lat1, lon2, lat2])
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1; dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return c * 6371 * 1000
    except Exception:
        return 0

# --- CHECKLIST STATUS LOGIC ---
def get_checklist_status(trigger_str, user_status, attempt_count):
    """
    Determines status based on MULTIPLE trigger times.
    trigger_str: "09:00,14:00"
    """
    if user_status == 'out':
        return 'LOCKED_OFF_DUTY'

    now = datetime.now() + IST_OFFSET
    current_minutes = now.hour * 60 + now.minute

    triggers = []
    if trigger_str:
        try:
            triggers = [t.strip() for t in trigger_str.split(',') if t.strip()]
        except Exception:
            triggers = [trigger_str]

    active_slot = None
    for t in triggers:
        try:
            th, tm = map(int, t.split(':'))
            trig_min = th * 60 + tm
            # Active Window: 30 mins before to 90 mins after
            if (trig_min - 30) <= current_minutes <= (trig_min + 90):
                active_slot = t
                break
        except Exception:
            continue

    if active_slot:
        if attempt_count >= 3:
            return 'LOCKED_MAX_ATTEMPTS'
        return 'ACTIVE'

    return 'LOCKED_FUTURE'

# --- SHIFT STATS ---
def calculate_shift_stats(user_id):
    """Calculates active work time based on punch history."""
    conn = get_db()
    c = conn.cursor()

    now = datetime.now() + IST_OFFSET
    shift_start = now.replace(hour=4, minute=0, second=0, microsecond=0)
    if now.hour < 4:
        shift_start -= timedelta(days=1)

    # Format shift_start as string to use in query
    start_str = shift_start.strftime('%Y-%m-%d %H:%M:%S')

    logs = c.execute(
        "SELECT action, timestamp FROM attendance WHERE user_id=? AND timestamp >= ? ORDER BY timestamp ASC",
        (user_id, start_str)).fetchall()
    conn.close()

    session_sec = 0
    work_sec = 0
    break_sec = 0
    current_status = 'out'
    last_action_time = None

    for log in logs:
        action = log['action']
        # guard against malformed timestamps
        try:
            ts = datetime.strptime(log['timestamp'][:19], '%Y-%m-%d %H:%M:%S')
        except Exception:
            continue

        if last_action_time:
            elapsed = (ts - last_action_time).total_seconds()
            if current_status == 'in':
                session_sec += elapsed
                work_sec += elapsed
            elif current_status == 'break':
                session_sec += elapsed
                break_sec += elapsed

        if action == 'in':
            current_status = 'in'
        elif action == 'out':
            current_status = 'out'
        elif action == 'break_start':
            current_status = 'break'
        elif action == 'break_end':
            current_status = 'in'

        last_action_time = ts

    if current_status != 'out' and last_action_time:
        elapsed = (now - last_action_time).total_seconds()
        session_sec += elapsed
        if current_status == 'in':
            work_sec += elapsed
        elif current_status == 'break':
            break_sec += elapsed

    return {
        'session_sec': int(session_sec),
        'work_sec': int(work_sec),
        'break_sec': int(break_sec),
        'status': current_status
    }