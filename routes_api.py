from flask import Blueprint, request, jsonify, session, current_app
from datetime import datetime, timedelta
import os
import database as db
import helpers as h
from werkzeug.utils import secure_filename

api_bp = Blueprint('api', __name__)

# Allowed extensions for evidence photos
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def _evidence_folder():
    # prefer app config, fallback to a safe path next to project
    folder = current_app.config.get('EVIDENCE_FOLDER')
    if not folder:
        base = os.path.dirname(os.path.abspath(__file__))
        folder = os.path.join(base, 'static', 'evidence')
    os.makedirs(folder, exist_ok=True)
    return folder

# --- CLOCK (POST JSON: {action: "in"|"out"|"break_start"|"break_end", lat, lon}) ---
@api_bp.route('/clock', methods=['POST'])
def clock():
    if 'user_id' not in session:
        return jsonify({'error': 'Auth'}), 401
    d = request.get_json() or {}
    action = d.get('action')
    lat = d.get('lat')
    lon = d.get('lon')
    ts = (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d %H:%M:%S')
    try:
        with db.get_db() as conn:
            conn.execute(
                "INSERT INTO attendance (user_id, action, timestamp, lat, lon) VALUES (?, ?, ?, ?, ?)",
                (session['user_id'], action, ts, lat, lon)
            )
            conn.commit()
        return jsonify({'status': 'success', 'timestamp': ts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- TASKS (supports checkboxes in form and file uploads safely) ---
@api_bp.route('/submit_checklist', methods=['POST'])
def submit():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        uid = session['user_id']
        cid = request.form.get('checklist_id')
        ts = (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d %H:%M:%S')

        with db.get_db() as conn:
            # 1. Handle Checkboxes/text items
            for k, v in request.form.items():
                if k == 'checklist_id':
                    continue
                # store the value; here v can be 'on' or some text
                conn.execute(
                    "INSERT INTO checklist_logs (checklist_id, user_id, task_name, data, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (cid, uid, k, v if v is not None else 'done', ts)
                )

            # 2. Handle Photos securely
            evidence_folder = _evidence_folder()
            for key in request.files:
                file = request.files[key]
                if file and file.filename:
                    if not allowed_file(file.filename):
                        # skip unsafe extension
                        continue
                    filename = secure_filename(file.filename)
                    filename = f"{uid}_{cid}_{int(datetime.now().timestamp())}_{filename}"
                    save_path = os.path.join(evidence_folder, filename)
                    file.save(save_path)
                    db_url = f"/static/evidence/{filename}"
                    conn.execute(
                        "INSERT INTO checklist_logs (checklist_id, user_id, task_name, task_type, photo_proof, timestamp) VALUES (?, ?, ?, 'PHOTO', ?, ?)",
                        (cid, uid, key, db_url, ts)
                    )
            conn.commit()
        return jsonify({'status': 'saved'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- TO-DO LIST ---
@api_bp.route('/todo/add', methods=['POST'])
def add_todo():
    if 'user_id' not in session:
        return jsonify({'error': 'Auth'}), 401
    txt = request.form.get('task')
    due = request.form.get('due_date')
    now_str = (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d %H:%M:%S')
    try:
        with db.get_db() as conn:
            conn.execute(
                "INSERT INTO todos (user_id, task, status, created_at, due_date) VALUES (?, ?, ?, ?, ?)",
                (session['user_id'], txt, 'pending', now_str, due)
            )
            conn.commit()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/todo/toggle', methods=['POST'])
def toggle_todo():
    if 'user_id' not in session:
        return jsonify({'error': 'Auth'}), 401
    tid = request.form.get('id')
    try:
        with db.get_db() as conn:
            conn.execute("UPDATE todos SET status='archived' WHERE id=?", (tid,))
            conn.commit()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/todo/delete', methods=['POST'])
def delete_todo():
    if 'user_id' not in session:
        return jsonify({'error': 'Auth'}), 401
    try:
        with db.get_db() as conn:
            conn.execute("DELETE FROM todos WHERE id=?", (request.form.get('id'),))
            conn.commit()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- ADMIN: incremental updates endpoint (existing) ---
@api_bp.route('/admin/updates')
def admin_updates():
    if session.get('user_role') != 'manager':
        return jsonify({'error': 'Unauthorized'}), 403
    since = request.args.get('since')
    if not since:
        since = (datetime.now() - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        with db.get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM attendance WHERE timestamp > ? ORDER BY timestamp DESC LIMIT 500",
                (since,)
            ).fetchall()
            attendance = [dict(r) for r in rows]
            logs = conn.execute(
                "SELECT * FROM checklist_logs WHERE timestamp > ? ORDER BY timestamp DESC LIMIT 500",
                (since,)
            ).fetchall()
            checklist = [dict(r) for r in logs]
        return jsonify({'attendance': attendance, 'checklist': checklist}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- NEW: get_live_data authoritative snapshot for admin dashboard ---
@api_bp.route('/get_live_data')
def get_live_data():
    if session.get('user_role') != 'manager':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        now = datetime.now() + h.IST_OFFSET
        # Shift window: start at 04:00 local
        shift_start = now.replace(hour=4, minute=0, second=0, microsecond=0)
        if now.hour < 4:
            shift_start -= timedelta(days=1)
        start_str = shift_start.strftime('%Y-%m-%d %H:%M:%S')

        # Get office config for location checks if present
        sys_conf = db.get_system_config()
        office_lat = sys_conf.get('lat')
        office_lon = sys_conf.get('lon')
        office_rad = sys_conf.get('rad', 500)

        with db.get_db() as conn:
            users_rows = conn.execute("SELECT id, name, role, department FROM users WHERE role != 'manager' ORDER BY id").fetchall()
            users = [dict(u) for u in users_rows]

            # Preload attendance rows from shift_start (fast lookup)
            att_rows = conn.execute("SELECT * FROM attendance WHERE timestamp >= ? ORDER BY timestamp ASC", (start_str,)).fetchall()
            att = [dict(r) for r in att_rows]

            staff_data = []
            for u in users:
                uid = u['id']
                # attendance for this user within shift window
                u_att = [r for r in att if r.get('user_id') == uid]

                session_start = None
                session_start_ts = None
                total_seconds = 0
                current_status = 'out'

                for r in u_att:
                    action = r.get('action')
                    ts_str = r.get('timestamp', '')[:19]
                    try:
                        ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                    except Exception:
                        continue

                    if action in ['in', 'break_end']:
                        # start or resume
                        session_start = ts
                        if session_start_ts is None:
                            session_start_ts = ts.strftime('%Y-%m-%d %H:%M:%S')
                        current_status = 'in'
                    elif action in ['out', 'break_start']:
                        if session_start:
                            total_seconds += (ts - session_start).total_seconds()
                            session_start = None
                        if action == 'out':
                            current_status = 'out'
                        else:
                            current_status = 'break'

                if session_start:
                    total_seconds += (now - session_start).total_seconds()
                    current_status = 'in'

                # last attendance row for location (if present)
                last = u_att[-1] if u_att else None
                lat = last.get('lat') if last and 'lat' in last else None
                lon = last.get('lon') if last and 'lon' in last else None
                # location check: use haversine if lat/lon present
                location_ok = False
                try:
                    if lat is not None and lon is not None and office_lat is not None and office_lon is not None:
                        dist = h.haversine(office_lon, office_lat, lon, lat)
                        location_ok = dist <= int(office_rad)
                except Exception:
                    location_ok = False

                staff_data.append({
                    'id': uid,
                    'name': u.get('name'),
                    'role': u.get('role'),
                    'department': u.get('department'),
                    'status': current_status,  # 'in'|'out'|'break'
                    'session_start_ts': session_start_ts,  # or None
                    'duration_ms': int(total_seconds * 1000),
                    'location_ok': bool(location_ok)
                })

        # summary
        summary = {
            'on_duty': sum(1 for s in staff_data if s['status'] == 'in'),
            'on_break': sum(1 for s in staff_data if s['status'] == 'break'),
            'out': sum(1 for s in staff_data if s['status'] == 'out')
        }

        return jsonify({'summary': summary, 'staff': staff_data}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/request_refill', methods=['POST'])
def request_refill():
    if 'user_id' not in session:
        return jsonify({'error': 'Auth'}), 401
    cid = request.form.get('checklist_id')
    uid = session['user_id']
    ts = (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d %H:%M:%S')
    try:
        with db.get_db() as conn:
            conn.execute(
                "INSERT INTO requests (user_id, checklist_id, request_type, status, timestamp) VALUES (?, ?, 'REFILL', 'PENDING', ?)",
                (uid, cid, ts)
            )
            conn.commit()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/acknowledge', methods=['POST'])
def acknowledge():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    aid = request.form.get('announcement_id')
    ts = (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d %H:%M:%S')
    try:
        with db.get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO acknowledgments (user_id, announcement_id, timestamp) VALUES (?, ?, ?)",
                (session['user_id'], aid, ts)
            )
            conn.commit()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500