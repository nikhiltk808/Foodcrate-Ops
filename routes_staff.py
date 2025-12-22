from flask import Blueprint, render_template, session, redirect, url_for
from datetime import datetime, timedelta
import json
import database as db
import helpers as h

staff_bp = Blueprint('staff', __name__)

@staff_bp.route('/staff/<int:route_user_id>')
def dashboard(route_user_id):
    if 'user_id' not in session: return redirect(url_for('admin.login'))
    if session['user_id'] != route_user_id and session.get('user_role') != 'manager':
        return redirect(url_for('staff.dashboard', route_user_id=session['user_id']))

    conn = db.get_db(); c = conn.cursor()

    # 1. SETUP
    now = datetime.now() + h.IST_OFFSET
    today_str = now.strftime('%d %b %Y')
    shift_start = now.replace(hour=4, minute=0, second=0, microsecond=0)
    if now.hour < 4: shift_start -= timedelta(days=1)

    # 2. STATUS
    last = c.execute("SELECT action, timestamp FROM attendance WHERE user_id=? ORDER BY timestamp DESC LIMIT 1", (route_user_id,)).fetchone()
    current_status = 'out'
    if last:
        try:
            if datetime.strptime(last['timestamp'][:19], '%Y-%m-%d %H:%M:%S') >= shift_start:
                if last['action'] in ['in', 'break_end']: current_status = 'in'
                elif last['action'] == 'break_start': current_status = 'break'
        except: pass

    # 3. STATS & LOGS
    stats = h.calculate_shift_stats(route_user_id)
    stats['status'] = current_status
    raw_logs = c.execute("SELECT action, timestamp FROM attendance WHERE user_id=? AND timestamp >= ? ORDER BY timestamp DESC", (route_user_id, shift_start)).fetchall()
    logs = [{'date_str': datetime.strptime(l['timestamp'][:19], '%Y-%m-%d %H:%M:%S').strftime('%d %b'),
             'time_str': datetime.strptime(l['timestamp'][:19], '%Y-%m-%d %H:%M:%S').strftime('%H:%M'),
             'action': l['action'].replace('_', ' ').title()} for l in raw_logs]

    # 4. BANNERS (UPDATED FOR MULTIPLE ITEMS)
    # Fetch ALL active announcements
    active_anns = c.execute("SELECT * FROM announcements WHERE is_active=1 ORDER BY created_at DESC").fetchall()
    updates = []
    for a in active_anns:
        item = dict(a)
        if item['meta_info']: item['meta_list'] = item['meta_info'].split('|')
        # Check read status per item
        ack = c.execute("SELECT 1 FROM acknowledgments WHERE user_id=? AND announcement_id=?", (route_user_id, item['id'])).fetchone()
        item['is_read'] = True if ack else False
        updates.append(item)

    # Fetch ALL active duties
    active_duties = c.execute("SELECT * FROM duty_instructions WHERE is_active=1 ORDER BY created_at DESC").fetchall()
    duties = []
    for d in active_duties:
        item = dict(d)
        try:
            item['lines'] = item['content'].split('\n')
            item['reporting_time'] = item.get('reporting_time', '00:00')
        except: pass
        duties.append(item)

    # 5. TO-DOS
    todos = []
    try:
        raw_todos = c.execute("SELECT * FROM todos WHERE user_id=? AND status='pending' ORDER BY id DESC", (route_user_id,)).fetchall()
        for t in raw_todos:
            item = dict(t)
            if item.get('due_date'):
                try:
                    dt = datetime.strptime(item['due_date'], '%Y-%m-%dT%H:%M')
                    item['time_display'] = dt.strftime('%d %b, %I:%M %p')
                except: item['time_display'] = item['due_date']
            else: item['time_display'] = "No Date"
            todos.append(item)
    except: pass

    # 6. CHECKLISTS (CATEGORIZED)
    saved = {}; attempts = {}; audit = {}; durations = []
    try:
        done = c.execute("SELECT checklist_id, task_name, timestamp FROM checklist_logs WHERE user_id=? AND timestamp >= ?", (route_user_id, shift_start)).fetchall()
        sub_times = {}
        for l in done:
            cid = l['checklist_id']
            if cid not in sub_times: sub_times[cid] = set()
            sub_times[cid].add(l['timestamp'])
            if cid not in saved: saved[cid] = {}
            if l['task_name']: saved[cid][l['task_name']] = 'done'
            if cid not in audit: audit[cid] = {'timestamps': []}
            audit[cid]['timestamps'].append(datetime.strptime(l['timestamp'][:19], '%Y-%m-%d %H:%M:%S'))
        for cid, t in sub_times.items(): attempts[cid] = len(t)
        for cid, a in audit.items():
            ts = sorted(a['timestamps'])
            if len(ts) > 1: durations.append((ts[-1] - ts[0]).total_seconds() / 60)
    except: pass

    snapshot = {'avg_time': f"{int(sum(durations)/len(durations))}m" if durations else "-", 'completed_count': len(durations)}

    # --- CATEGORIZATION LOGIC ---
    kpi = {'completed':0, 'pending':0, 'overdue':0}
    task_groups = {'active': [], 'upcoming': [], 'completed': [], 'quick': []}

    rows = c.execute("SELECT * FROM checklists").fetchall()

    for r in rows:
        assigns = str(r['assigned_to']).split(',') if r['assigned_to'] else ['all']
        if 'all' in assigns or str(route_user_id) in assigns:
            try:
                item = dict(r)
                try: item['task_items'] = [({'title': t, 'is_photo': False} if isinstance(t, str) else t) for t in json.loads(r['tasks'])]
                except: item['task_items'] = []
                item['saved_data'] = saved.get(r['id'], {})
                item['attempt_count'] = attempts.get(r['id'], 0)
                item['status'] = h.get_checklist_status(r['trigger_time'], current_status, item['attempt_count'])
                item['estimated_time'] = (r['id'] * 2) + 3

                try:
                    # Multiple triggers handling for sorting
                    first_trigger = r['trigger_time'].split(',')[0]
                    th, tm = map(int, first_trigger.split(':'))
                    trig_dt = now.replace(hour=th, minute=tm, second=0)
                    item['activates_str'] = f"{now.strftime('%d %b')}, {first_trigger}"
                    exp_dt = trig_dt + timedelta(minutes=90)
                    delta = (trig_dt - now).total_seconds() / 60
                    if delta < 30 and delta > -90: item['priority'] = 'High'
                    elif delta < 60 and delta > -90: item['priority'] = 'Medium'
                    else: item['priority'] = 'Low'
                    item['sort_val'] = delta
                    left = (exp_dt - now).total_seconds()
                    if left > 0 and left < 5400: item['minutes_left'] = int(left // 60)
                except: item['priority']='Low'; item['sort_val']=999; item['activates_str']=r['trigger_time']

                req = c.execute("SELECT status FROM requests WHERE user_id=? AND checklist_id=? AND status='PENDING'", (route_user_id, r['id'])).fetchone()
                item['refill_pending'] = True if req else False

                ts_list = sorted(audit.get(r['id'], {'timestamps':[]})['timestamps'])
                if ts_list:
                    item['start_time'] = ts_list[0].strftime('%I:%M %p'); item['end_time'] = ts_list[-1].strftime('%I:%M %p')
                    d_sec = (ts_list[-1] - ts_list[0]).total_seconds()
                    item['duration'] = f"{int(d_sec//60)}m" if d_sec >= 60 else f"{int(d_sec)}s"
                else: item['start_time']="-"; item['duration']="0m"

                pct = (len(item['saved_data']) / len(item['task_items']) * 100) if item['task_items'] else 0

                if pct == 100 or item['status'] == 'COMPLETED': kpi['completed'] += 1
                elif item['status'] in ['EXPIRED', 'LOCKED_MAX_ATTEMPTS']: kpi['overdue'] += 1
                elif item['status'] in ['ACTIVE', 'ACTIVE_PARTIAL']: kpi['pending'] += 1

                is_quick = item.get('frequency') == 'One-Time'
                is_done = (pct == 100 or item['status'] == 'COMPLETED' or item['status'] in ['EXPIRED', 'LOCKED_MAX_ATTEMPTS'])

                if is_done: task_groups['completed'].append(item)
                elif is_quick: task_groups['quick'].append(item)
                elif item['status'] in ['ACTIVE', 'ACTIVE_PARTIAL']: task_groups['active'].append(item)
                else: task_groups['upcoming'].append(item)

            except: pass
    conn.close()

    sorter = lambda x: ({'High':0, 'Medium':1, 'Low':2}.get(x.get('priority'), 2), x.get('sort_val', 999))
    for key in task_groups: task_groups[key].sort(key=sorter)

    return render_template('dashboard_staff.html', theme=h.THEME, user=session['user_name'],
                           current_status=current_status, tasks=task_groups, stats=stats,
                           kpi=kpi, current_date=today_str,
                           updates=updates, # CHANGED: Passing list
                           duties=duties,   # CHANGED: Passing list
                           snapshot=snapshot,
                           todos=todos, logs=logs,
                           route_user_id=route_user_id,
                           user_role=session.get('user_role'))

@staff_bp.route('/staff/checklist/<int:cid>')
def view_checklist(cid):
    if 'user_id' not in session: return redirect(url_for('admin.login'))
    with db.get_db() as conn:
        chk = conn.execute("SELECT * FROM checklists WHERE id=?", (cid,)).fetchone()
        tasks = json.loads(chk['tasks']) if chk and chk['tasks'] else []
    return render_template('staff_checklist_form.html', theme=h.THEME, checklist=chk, tasks=tasks)