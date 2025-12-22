from flask import (
    Blueprint, render_template, request, session, redirect, url_for,
    Response, jsonify, current_app, send_file
)
from datetime import datetime, timedelta
import csv
import io
import zipfile
import json
import math
import os

import database as db
import helpers as h

admin_bp = Blueprint('admin', __name__)

# --- CONFIGURATION (defaults; can be overridden in DB/system_settings) ---
WORK_LAT = 12.9716
WORK_LON = 77.5946
ALLOWED_RADIUS_METERS = 500


def is_in_location(lat, lon):
    """Return True if (lat,lon) is within ALLOWED_RADIUS_METERS of work location."""
    try:
        if lat is None or lon is None:
            return False
        # helpers.haversine expects (lon1, lat1, lon2, lat2)
        dist = h.haversine(WORK_LON, WORK_LAT, float(lon), float(lat))
        return dist <= ALLOWED_RADIUS_METERS
    except Exception:
        return False


# --- AUTH ---
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        pin = request.form.get('pin')
        with db.get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE name = ? AND pin = ?", (name, pin)).fetchone()
            if user:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_role'] = user['role']
                # Redirect based on role
                if user['role'] == 'manager':
                    return redirect(url_for('admin.home'))
                else:
                    return redirect(url_for('staff.dashboard', route_user_id=user['id']))
    return render_template('login.html', theme=h.THEME)


@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


# --- DASHBOARD (home) ---
@admin_bp.route('/')
def home():
    # Only manager may access admin home
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))

    conn = db.get_db()
    c = conn.cursor()

    date_str = request.args.get('date', (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d'))
    try:
        current_date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    except Exception:
        current_date_obj = datetime.now() + h.IST_OFFSET
        date_str = current_date_obj.strftime('%Y-%m-%d')

    prev_date = (current_date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (current_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
    is_today = (date_str == (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d'))
    now_ist = datetime.now() + h.IST_OFFSET

    # Fetch users (exclude managers)
    users = c.execute("SELECT * FROM users WHERE role != 'manager'").fetchall()

    # Fetch attendance for the day
    daily_logs = c.execute(
        "SELECT * FROM attendance WHERE date(timestamp) = ? ORDER BY timestamp ASC", (date_str,)
    ).fetchall()

    staff_status = []
    for u in users:
        # u is sqlite3.Row — access via keys like u['id']
        u_logs = [l for l in daily_logs if l['user_id'] == u['id']]
        total_seconds = 0
        session_start = None
        session_start_ts = None  # Keep ISO string of the active session start if any

        for log in u_logs:
            try:
                ts = datetime.strptime(log['timestamp'][:19], '%Y-%m-%d %H:%M:%S')
            except Exception:
                continue
            if log['action'] in ['in', 'break_end']:
                session_start = ts
                # capture the first open session start timestamp for display
                if session_start_ts is None:
                    session_start_ts = ts.strftime('%Y-%m-%d %H:%M:%S')
            elif log['action'] in ['out', 'break_start']:
                if session_start:
                    total_seconds += (ts - session_start).total_seconds()
                    session_start = None
                    session_start_ts = None  # closed

        is_active = False
        if session_start and is_today:
            total_seconds += (now_ist - session_start).total_seconds()
            is_active = True
            if session_start_ts is None:
                session_start_ts = session_start.strftime('%Y-%m-%d %H:%M:%S')

        status = 'OFF DUTY'
        color = 'gray'
        location_ok = False

        if u_logs:
            last_row = u_logs[-1]
            last = dict(last_row)
            # Determine status based on last action (prefer today's view)
            if is_today:
                act = last.get('action')
                if act in ['in', 'break_end']:
                    status = 'ON DUTY'; color = 'green'; is_active = True
                elif act == 'break_start':
                    status = 'ON BREAK'; color = 'orange'; is_active = False
                elif act == 'out':
                    status = 'CLOCKED OUT'; color = 'gray'; is_active = False
            else:
                status = "LOGGED"; is_active = False

            lat = last.get('lat')
            lon = last.get('lon')
            location_ok = is_in_location(lat, lon)
        else:
            status = 'OFF DUTY'; color = 'gray'; is_active = False; location_ok = False

        staff_status.append({
            'id': u['id'],
            'name': u['name'],
            'dept': u['department'],
            'status': status,
            'color': color,
            'duration_ms': int(total_seconds * 1000),
            'is_active': bool(is_active),
            'location_ok': bool(location_ok),
            'session_start_ts': session_start_ts
        })

    # Fetch active duty instructions and announcements
    active_duties = [dict(r) for r in c.execute(
        "SELECT * FROM duty_instructions WHERE is_active=1 ORDER BY created_at DESC"
    ).fetchall()]
    active_anns = [dict(r) for r in c.execute(
        "SELECT * FROM announcements WHERE is_active=1 ORDER BY created_at DESC"
    ).fetchall()]

    duty_history = [dict(r) for r in c.execute(
        "SELECT * FROM duty_instructions ORDER BY id DESC LIMIT 20"
    ).fetchall()]
    ann_history = [dict(r) for r in c.execute(
        "SELECT * FROM announcements ORDER BY id DESC LIMIT 20"
    ).fetchall()]

    conn.close()

    return render_template('dashboard_admin.html', theme=h.THEME,
                           user=session.get('user_name'),
                           staff=staff_status,
                           active_duties=active_duties,
                           active_anns=active_anns,
                           duty_history=duty_history,
                           ann_history=ann_history,
                           date=date_str, prev=prev_date, next=next_date, is_today=is_today)


# --- BROADCASTING (create / archive duties & announcements) ---
@admin_bp.route('/admin/set_duty', methods=['POST'])
def set_duty():
    if session.get('user_role') != 'manager':
        return "Unauthorized", 403
    title = request.form.get('title')
    event_date = request.form.get('date')
    reporting_time = request.form.get('time')
    content = request.form.get('content')
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO duty_instructions (title, event_date, reporting_time, content, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            (title, event_date, reporting_time, content, now_ts)
        )
        conn.commit()
    return redirect(url_for('admin.home'))


@admin_bp.route('/admin/set_announcement', methods=['POST'])
def set_announcement():
    if session.get('user_role') != 'manager':
        return "Unauthorized", 403
    title = request.form.get('title')
    message = request.form.get('message')
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO announcements (title, message, is_active, created_at) VALUES (?, ?, 1, ?)",
            (title, message, now_ts)
        )
        conn.commit()
    return redirect(url_for('admin.home'))


# --- ARCHIVE / CLEAR ---
@admin_bp.route('/admin/archive_duty/<int:id>')
def archive_duty(id):
    if session.get('user_role') != 'manager':
        return "Unauthorized", 403
    with db.get_db() as conn:
        conn.execute("UPDATE duty_instructions SET is_active=0 WHERE id=?", (id,))
        conn.commit()
    return redirect(url_for('admin.home'))


@admin_bp.route('/admin/archive_announcement/<int:id>')
def archive_announcement(id):
    if session.get('user_role') != 'manager':
        return "Unauthorized", 403
    with db.get_db() as conn:
        conn.execute("UPDATE announcements SET is_active=0 WHERE id=?", (id,))
        conn.commit()
    return redirect(url_for('admin.home'))


@admin_bp.route('/admin/clear_banners')
def clear_banners():
    if session.get('user_role') != 'manager':
        return "Unauthorized", 403
    with db.get_db() as conn:
        conn.execute("UPDATE duty_instructions SET is_active=0")
        conn.execute("UPDATE announcements SET is_active=0")
        conn.commit()
    return redirect(url_for('admin.home'))


# --- CHECKLISTS (basic CRUD pages and library context) ---
def _build_checklist_context(edit_id=None):
    """Helper to gather users, checklists, mappings and analytics for the admin checklist page."""
    with db.get_db() as conn:
        users_rows = conn.execute("SELECT * FROM users").fetchall()
        users = [dict(u) for u in users_rows]

        # user_map: string id -> name for template lookup
        user_map = {str(u['id']): u['name'] for u in users}

        checklists_rows = conn.execute("SELECT * FROM checklists ORDER BY id DESC").fetchall()
        checklists = []
        for l in checklists_rows:
            ll = dict(l)
            # populate convenience fields expected by template
            ll['depts'] = ll.get('assigned_to') or ''
            ll['staff_ids'] = ll.get('assigned_to') or 'all'
            # compute total_filled / fill_count by counting checklist_logs entries for the checklist
            try:
                cnt = conn.execute("SELECT COUNT(DISTINCT timestamp) as c FROM checklist_logs WHERE checklist_id=?", (ll['id'],)).fetchone()
                ll['total_filled'] = cnt['c'] if cnt else 0
            except Exception:
                ll['total_filled'] = 0
            checklists.append(ll)

        # analytics (simple)
        today = (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d')
        try:
            today_logs = conn.execute("SELECT COUNT(*) as c FROM attendance WHERE date(timestamp)=?", (today,)).fetchone()['c']
        except Exception:
            today_logs = 0
        try:
            total_submissions = conn.execute("SELECT COUNT(*) as c FROM checklist_logs").fetchone()['c']
        except Exception:
            total_submissions = 0

        analytics = {'today': today_logs, 'total_submissions': total_submissions}

        # If edit_id provided, fetch checklist row
        checklist = None
        if edit_id:
            r = conn.execute("SELECT * FROM checklists WHERE id=?", (edit_id,)).fetchone()
            if r:
                checklist = dict(r)

    return {'users': users, 'checklists': checklists, 'user_map': user_map, 'analytics': analytics, 'checklist': checklist}


@admin_bp.route('/admin/checklists')
def checklist_manager():
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))

    ctx = _build_checklist_context()
    # render template with all required context variables
    return render_template('admin_checklists.html',
                           theme=h.THEME,
                           user=session.get('user_name'),
                           users=ctx['users'],
                           checklists=ctx['checklists'],
                           user_map=ctx['user_map'],
                           analytics=ctx['analytics'],
                           checklist=ctx['checklist'])


@admin_bp.route('/admin/save_checklist', methods=['POST'])
def save_checklist():
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))

    # Read form fields
    title = request.form.get('title') or 'Untitled'
    # tasks_json contains JSON array built on client
    tasks_json = request.form.get('tasks_json') or '[]'
    # assigned_to may be multiple form values - use getlist
    assigned = request.form.getlist('assigned_to')
    if not assigned:
        assigned_to = 'all'
    else:
        # If all users were selected, mark 'all'
        with db.get_db() as conn:
            all_uids = [str(u['id']) for u in conn.execute("SELECT id FROM users").fetchall()]
        if set(map(str, assigned)) >= set(all_uids):
            assigned_to = 'all'
        else:
            assigned_to = ','.join([str(a) for a in assigned])

    # frequency_final may be set by client for weekly selection
    frequency_final = request.form.get('frequency_final') or request.form.get('frequency') or ''
    trigger_time = ','.join(request.form.getlist('trigger_time[]')) if request.form.getlist('trigger_time[]') else request.form.get('trigger_time') or ''

    with db.get_db() as conn:
        # If list_id present -> update, else insert
        list_id = request.form.get('list_id')
        if list_id:
            conn.execute("UPDATE checklists SET title=?, tasks=?, assigned_to=?, frequency=?, trigger_time=? WHERE id=?",
                         (title, tasks_json, assigned_to, frequency_final, trigger_time, list_id))
        else:
            conn.execute("INSERT INTO checklists (title, tasks, assigned_to, frequency, trigger_time) VALUES (?, ?, ?, ?, ?)",
                         (title, tasks_json, assigned_to, frequency_final, trigger_time))
        conn.commit()

    return redirect(url_for('admin.checklist_manager'))


@admin_bp.route('/admin/duplicate_checklist/<int:lid>')
def duplicate_checklist(lid):
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM checklists WHERE id=?", (lid,)).fetchone()
        if row:
            conn.execute(
                "INSERT INTO checklists (title, tasks, assigned_to, frequency, trigger_time) VALUES (?, ?, ?, ?, ?)",
                (row['title'] + " (copy)", row['tasks'], row['assigned_to'], row['frequency'], row['trigger_time'])
            )
            conn.commit()
    return redirect(url_for('admin.checklist_manager'))


@admin_bp.route('/admin/toggle_checklist/<int:lid>')
def toggle_checklist(lid):
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))
    # If you want an 'active' flag, implement it in DB and toggle here.
    # For now just redirect back.
    return redirect(url_for('admin.checklist_manager'))


@admin_bp.route('/admin/delete_checklist/<int:lid>')
def delete_checklist(lid):
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))
    with db.get_db() as conn:
        conn.execute("DELETE FROM checklists WHERE id=?", (lid,))
        conn.commit()
    return redirect(url_for('admin.checklist_manager'))


@admin_bp.route('/admin/edit_checklist/<int:lid>')
def edit_checklist(lid):
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))
    ctx = _build_checklist_context(edit_id=lid)
    return render_template('admin_checklists.html',
                           theme=h.THEME,
                           user=session.get('user_name'),
                           users=ctx['users'],
                           checklists=ctx['checklists'],
                           user_map=ctx['user_map'],
                           analytics=ctx['analytics'],
                           checklist=ctx['checklist'])


# --- EVIDENCE (photos) ---
# ---------------------------------------
# Evidence gallery: filtering by date & staff
# ---------------------------------------
@admin_bp.route('/admin/evidence')
def evidence():
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))

    # parse date and staff filters
    selected_date = request.args.get('date', (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d'))
    selected_staff = request.args.get('staff_id', 'all')

    # compute prev/next for nav
    try:
        dt = datetime.strptime(selected_date, '%Y-%m-%d')
    except Exception:
        dt = datetime.now() + h.IST_OFFSET
        selected_date = dt.strftime('%Y-%m-%d')
    prev_date = (dt - timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (dt + timedelta(days=1)).strftime('%Y-%m-%d')

    with db.get_db() as conn:
        # build query
        base_q = """
            SELECT cl.id, cl.user_id, cl.checklist_id, cl.task_name, cl.photo_proof, cl.timestamp, u.name as staff_name, ch.title as checklist_title
            FROM checklist_logs cl
            LEFT JOIN users u ON cl.user_id = u.id
            LEFT JOIN checklists ch ON cl.checklist_id = ch.id
            WHERE cl.photo_proof IS NOT NULL AND date(cl.timestamp)=?
        """
        params = [selected_date]
        if selected_staff and selected_staff != 'all':
            base_q += " AND cl.user_id = ?"
            params.append(selected_staff)
        base_q += " ORDER BY cl.timestamp DESC"
        rows = conn.execute(base_q, params).fetchall()
        photos = [dict(r) for r in rows]

        # users for filter dropdown
        users = [dict(u) for u in conn.execute("SELECT id, name FROM users ORDER BY name").fetchall()]

    return render_template('evidence_wall.html', theme=h.THEME, user=session.get('user_name'),
                           photos=photos, users=users,
                           selected_date=selected_date, prev_date=prev_date, next_date=next_date,
                           selected_staff=selected_staff)


# ---------------------------------------
# Delete evidence (single or bulk by date range)
# ---------------------------------------
@admin_bp.route('/admin/evidence/delete', methods=['POST'])
def delete_evidence():
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))

    target = request.form.get('target')  # 'single' or 'date_range'
    with db.get_db() as conn:
        if target == 'single' or request.form.get('photo_id'):
            photo_id = request.form.get('photo_id') or request.form.get('id')
            if not photo_id:
                return redirect(url_for('admin.evidence'))
            row = conn.execute("SELECT photo_proof FROM checklist_logs WHERE id=?", (photo_id,)).fetchone()
            if row and row['photo_proof'] and row['photo_proof'].startswith('/static/'):
                full = os.path.join(current_app.root_path, row['photo_proof'].lstrip('/'))
                try:
                    if os.path.exists(full):
                        os.remove(full)
                except Exception:
                    pass
            conn.execute("DELETE FROM checklist_logs WHERE id=?", (photo_id,))
            conn.commit()
            return redirect(url_for('admin.evidence'))

        # else date_range deletion
        # date_ref can be "YYYY-MM-DD|YYYY-MM-DD" or there may be start_date/end_date fields
        date_ref = request.form.get('date_ref') or ''
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        staff_id = request.form.get('staff_id', 'all')
        if date_ref and '|' in date_ref:
            start_date, end_date = date_ref.split('|', 1)
        if not start_date or not end_date:
            return "Invalid date range", 400

        q = "SELECT id, photo_proof FROM checklist_logs WHERE date(timestamp) >= ? AND date(timestamp) <= ?"
        params = [start_date, end_date]
        if staff_id and staff_id != 'all':
            q += " AND user_id = ?"
            params.append(staff_id)
        rows = conn.execute(q, params).fetchall()
        ids = [r['id'] for r in rows]
        # Delete files
        for r in rows:
            pp = r['photo_proof']
            if pp and pp.startswith('/static/'):
                full = os.path.join(current_app.root_path, pp.lstrip('/'))
                try:
                    if os.path.exists(full):
                        os.remove(full)
                except Exception:
                    pass
        # Delete DB rows
        if ids:
            qdel = f"DELETE FROM checklist_logs WHERE id IN ({','.join(['?']*len(ids))})"
            conn.execute(qdel, ids)
            conn.commit()
        return redirect(url_for('admin.evidence'))


# ---------------------------------------
# Export evidence as ZIP (date range + optional staff)
# ---------------------------------------
@admin_bp.route('/admin/evidence/export', methods=['POST'])
def export_evidence():
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))

    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    staff_id = request.form.get('staff_id', 'all')

    if not start_date or not end_date:
        return "start_date and end_date required", 400

    with db.get_db() as conn:
        q = """
            SELECT cl.id, cl.user_id, cl.checklist_id, cl.task_name, cl.photo_proof, cl.timestamp, u.name as staff_name
            FROM checklist_logs cl
            LEFT JOIN users u ON cl.user_id = u.id
            WHERE cl.photo_proof IS NOT NULL
              AND date(cl.timestamp) >= ? AND date(cl.timestamp) <= ?
        """
        params = [start_date, end_date]
        if staff_id and staff_id != 'all':
            q += " AND cl.user_id = ?"
            params.append(staff_id)
        rows = conn.execute(q, params).fetchall()
        rows = [dict(r) for r in rows]

    # Create in-memory ZIP: add files if present and a metadata CSV
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        # metadata CSV
        meta = io.StringIO()
        cw = csv.writer(meta)
        cw.writerow(['id', 'user_id', 'staff_name', 'checklist_id', 'task_name', 'photo_proof', 'timestamp'])
        for r in rows:
            cw.writerow([r['id'], r['user_id'], r['staff_name'], r['checklist_id'], r['task_name'], r['photo_proof'], r['timestamp']])
            # add the file to zip if it exists on disk
            if r['photo_proof'] and r['photo_proof'].startswith('/static/'):
                full = os.path.join(current_app.root_path, r['photo_proof'].lstrip('/'))
                if os.path.exists(full):
                    # Use a safer name in ZIP
                    arcname = f"evidence/{os.path.basename(full)}"
                    try:
                        zf.write(full, arcname)
                    except Exception:
                        pass
        # write metadata
        zf.writestr('metadata.csv', meta.getvalue())

    mem.seek(0)
    filename = f"evidence_{start_date}_to_{end_date}.zip"
    return send_file(mem, mimetype='application/zip', as_attachment=True, download_name=filename)


# --- USER ACTIVITY API (for admin modal) ---
@admin_bp.route('/admin/get_user_activity/<int:uid>')
def get_user_activity(uid):
    if session.get('user_role') != 'manager':
        return jsonify([])
    date_str = request.args.get('date', (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d'))
    logs = []
    with db.get_db() as conn:
        # Attendance
        rows = conn.execute(
            "SELECT action, timestamp FROM attendance WHERE user_id=? AND date(timestamp)=? ORDER BY timestamp ASC",
            (uid, date_str)
        ).fetchall()
        for r in rows:
            ts = r['timestamp'] or ''
            ttime = ts[11:19] if len(ts) >= 19 else ts
            logs.append({'date': ts[:10], 'action': r['action'], 'time': ttime})
        # Checklist logs
        clrows = conn.execute(
            "SELECT task_name, timestamp FROM checklist_logs WHERE user_id=? AND date(timestamp)=? ORDER BY timestamp ASC",
            (uid, date_str)
        ).fetchall()
        for r in clrows:
            ts = r['timestamp'] or ''
            ttime = ts[11:19] if len(ts) >= 19 else ts
            logs.append({'date': ts[:10], 'action': f"CHECKLIST: {r['task_name'] or ''}", 'time': ttime})
    # sort by time ascending
    logs_sorted = sorted(logs, key=lambda x: x.get('time') or '')
    return jsonify(logs_sorted)


# --- HISTORY / EXPORTS / SETTINGS ---
# ---------------------------
# HISTORY: timeline + report
# ---------------------------
@admin_bp.route('/admin/history')
def history():
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))

    # Accept date param (YYYY-MM-DD)
    date_str = request.args.get('date', (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d'))
    try:
        cur_date = datetime.strptime(date_str, '%Y-%m-%d')
    except Exception:
        cur_date = datetime.now() + h.IST_OFFSET
        date_str = cur_date.strftime('%Y-%m-%d')

    prev_date = (cur_date - timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (cur_date + timedelta(days=1)).strftime('%Y-%m-%d')

    with db.get_db() as conn:
        # Fetch attendance + checklist logs for the date and combine
        q = """
            SELECT 'attendance' as src, id, user_id, action as event, NULL as task_name, timestamp
            FROM attendance WHERE date(timestamp)=?
            UNION ALL
            SELECT 'checklist' as src, id, user_id, NULL as event, task_name, timestamp
            FROM checklist_logs WHERE date(timestamp)=?
            ORDER BY timestamp ASC
        """
        rows = conn.execute(q, (date_str, date_str)).fetchall()

        # Build a map of user_id -> name for quick lookup
        users_rows = conn.execute("SELECT id, name, department FROM users").fetchall()
        user_map = {r['id']: {'name': r['name'], 'dept': r['department']} for r in users_rows}

        timeline = []
        for r in rows:
            ts = r['timestamp'] or ''
            time_only = ts[11:16] if len(ts) >= 16 else ts
            if r['src'] == 'attendance':
                icon = 'login' if r['event'] == 'in' else ('logout' if r['event'] == 'out' else 'free_break')
                tl_type = 'attendance'
                detail = r['event']
            else:
                icon = 'task_alt'
                tl_type = 'task'
                detail = r['task_name'] or ''
            uname = user_map.get(r['user_id'], {}).get('name', f"User {r['user_id']}")
            timeline.append({
                'time': time_only,
                'type': tl_type,
                'icon': icon,
                'user': uname,
                'detail': detail,
                'action': r['event'] if r['src'] == 'attendance' else None
            })

        # Build attendance summary (per non-manager user)
        staff_rows = conn.execute("SELECT id, name, department FROM users WHERE role != 'manager' ORDER BY id").fetchall()
        report = []
        for s in staff_rows:
            # fetch attendance rows for this user on the date in chronological order
            arows = conn.execute("SELECT action, timestamp FROM attendance WHERE user_id=? AND date(timestamp)=? ORDER BY timestamp ASC", (s['id'], date_str)).fetchall()
            in_time = '-'; out_time = '-'; total_seconds = 0
            session_start = None
            for ar in arows:
                try:
                    ts = datetime.strptime(ar['timestamp'][:19], '%Y-%m-%d %H:%M:%S')
                except Exception:
                    continue
                if ar['action'] in ['in', 'break_end']:
                    if session_start is None:
                        session_start = ts
                    if in_time == '-':
                        in_time = ts.strftime('%H:%M')
                elif ar['action'] in ['out', 'break_start']:
                    if session_start:
                        total_seconds += (ts - session_start).total_seconds()
                        session_start = None
                        out_time = ts.strftime('%H:%M')  # keep updating to last out
            # if still active at end of day, count until now
            if session_start:
                now_ist = datetime.now() + h.IST_OFFSET
                total_seconds += (now_ist - session_start).total_seconds()
            status = 'Present' if in_time != '-' else 'Absent'
            # duration formatting
            hrs = int(total_seconds // 3600); mins = int((total_seconds % 3600) // 60)
            duration = f"{hrs}h {mins}m" if total_seconds > 0 else '-'
            report.append({
                'id': s['id'],
                'name': s['name'],
                'dept': s['department'],
                'status': status,
                'in': in_time,
                'out': out_time,
                'duration': duration
            })

    return render_template('admin_history.html', theme=h.THEME, user=session.get('user_name'),
                           timeline=timeline, report=report,
                           date=date_str, prev=prev_date, next=next_date)


# ---------------------------------------
# Download CSV for history (single date)
# ---------------------------------------
@admin_bp.route('/admin/history/download_csv')
def download_history_csv():
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))

    date_str = request.args.get('date', (datetime.now() + h.IST_OFFSET).strftime('%Y-%m-%d'))
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT 'ATT' as type, id, user_id, action as event, timestamp FROM attendance WHERE date(timestamp)=? "
            "UNION ALL "
            "SELECT 'CHK' as type, id, user_id, task_name as event, timestamp FROM checklist_logs WHERE date(timestamp)=? "
            "ORDER BY timestamp ASC",
            (date_str, date_str)
        ).fetchall()
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['type', 'id', 'user_id', 'event', 'timestamp'])
        for r in rows:
            cw.writerow([r['type'], r['id'], r['user_id'], r['event'], r['timestamp']])
        output = si.getvalue()
    filename = f"history_{date_str}.csv"
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": f"attachment; filename={filename}"})


@admin_bp.route('/admin/settings')
def settings():
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))
    with db.get_db() as conn:
        s = conn.execute("SELECT * FROM system_settings LIMIT 1").fetchone()
        users = [dict(u) for u in conn.execute("SELECT * FROM users ORDER BY id ASC").fetchall()]
    settings = dict(s) if s else {}
    return render_template('admin_settings.html', theme=h.THEME, user=session.get('user_name'), settings=settings, users=users)


@admin_bp.route('/admin/save_user', methods=['POST'])
def save_user():
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))
    name = request.form.get('name')
    pin = request.form.get('pin')
    role = request.form.get('role', 'staff')
    dept = request.form.get('department', '')
    with db.get_db() as conn:
        # If user_id present we would update; for now we only insert new users
        conn.execute("INSERT INTO users (name, pin, role, department) VALUES (?, ?, ?, ?)", (name, pin, role, dept))
        conn.commit()
    return redirect(url_for('admin.settings'))


@admin_bp.route('/admin/delete_user/<int:uid>')
def delete_user(uid):
    if session.get('user_role') != 'manager':
        return redirect(url_for('admin.login'))
    with db.get_db() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
    return redirect(url_for('admin.settings'))