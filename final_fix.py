import os

# --- 1. FIXED APP.PY CONTENT ---
app_code = r"""from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "zion_hills_secure_key"

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "zion_ops.db"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True) 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

THEME = {
    'primary': '#4F46E5', 'secondary': '#64748B', 'success': '#10B981', 
    'warning': '#F59E0B', 'danger': '#EF4444', 'bg': '#F8FAFC', 'card': '#FFFFFF'
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, pin TEXT, role TEXT, department TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, timestamp DATETIME)")
        conn.execute("CREATE TABLE IF NOT EXISTS checklist_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, checklist_id INTEGER, data TEXT, photo_path TEXT, timestamp DATETIME, edit_history TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS checklists (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, tasks TEXT, assigned_to TEXT, trigger_time TEXT, frequency TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS roster (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT, type TEXT, notes TEXT, UNIQUE(user_id, date))")
        try: conn.execute("INSERT INTO users (name, pin, role, department) VALUES ('Admin', '1234', 'manager', 'Admin')")
        except sqlite3.IntegrityError: pass

# --- ANALYTICS LOGIC ---
def get_admin_stats(user_dept):
    with get_db() as conn:
        if user_dept == 'Admin':
            users = conn.execute("SELECT id, name, department FROM users WHERE role != 'manager'").fetchall()
        else:
            users = conn.execute("SELECT id, name, department FROM users WHERE role != 'manager' AND department = ?", (user_dept,)).fetchall()
            
        today_logs = conn.execute("SELECT user_id, action, timestamp FROM attendance WHERE date(timestamp) = date('now')").fetchall()
        today_checks = conn.execute("SELECT user_id FROM checklist_logs WHERE date(timestamp) = date('now')").fetchall()
        check_counts = {}
        for c in today_checks: check_counts[c['user_id']] = check_counts.get(c['user_id'], 0) + 1

    staff_data = []; present = 0; late = 0; top_star = None; max_score = -1
    
    for u in users:
        uid = u['id']
        logs = [l for l in today_logs if l['user_id'] == uid]
        logs.sort(key=lambda x: x['timestamp'])
        
        status = 'OUT'; start = "-"; is_late = False; left = 0; width = 0
        if logs:
            last = logs[-1]
            if last['action'] in ['IN', 'BREAK_END']: status = 'IN'
            
            first = next((l for l in logs if l['action'] == 'IN'), None)
            if first:
                present += 1
                dt = datetime.strptime(first['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                start = dt.strftime("%H:%M")
                if dt.hour > 9 or (dt.hour == 9 and dt.minute > 30): 
                    is_late = True; late += 1
                
                h = dt.hour + (dt.minute/60)
                left = max(0, (h - 8) * 8)
                n = datetime.now()
                width = max(2, ((n.hour + n.minute/60) - h) * 8)

        checks = check_counts.get(uid, 0)
        score = (checks * 10) - (5 if is_late else 0)
        
        s_obj = {'id': uid, 'name': u['name'], 'dept': u['department'], 'status': status, 'start': start, 'checks': checks, 'is_late': is_late, 'score': score, 'bar_left': left, 'bar_width': width}
        staff_data.append(s_obj)
        if score > max_score and status != 'OUT': max_score = score; top_star = s_obj

    return {'staff': staff_data, 'total': len(users), 'present': present, 'late': late, 'top_star': top_star}

# --- ROUTES ---
@app.route('/')
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    if session.get('user_role') == 'manager':
        data = get_admin_stats(session.get('user_dept')) # FIX: Passed data correctly
        return render_template('dashboard_admin.html', theme=THEME, user=session['user_name'], dept=session.get('user_dept'), data=data)
    else:
        return redirect(url_for('staff_dashboard'))

@app.route('/staff_dashboard')
def staff_dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        lists = conn.execute("SELECT * FROM checklists").fetchall()
        my_lists = []
        for row in lists:
            r = dict(row)
            try: r['task_items'] = json.loads(r['tasks']) 
            except: r['task_items'] = []
            a = r['assigned_to'].split(',') if r['assigned_to'] else []
            if r['assigned_to'] == 'all' or str(session['user_id']) in a: my_lists.append(r)
    return render_template('dashboard_staff.html', theme=THEME, user=session['user_name'], checklists=my_lists)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name'); pin = request.form.get('pin')
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE name = ? AND pin = ?", (name, pin)).fetchone()
            if user:
                session['user_id'] = user['id']; session['user_name'] = user['name']
                session['user_role'] = user['role']; session['user_dept'] = user['department']
                return redirect(url_for('home'))
            else: return render_template('login.html', theme=THEME, error="Invalid")
    return render_template('login.html', theme=THEME)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/admin/settings')
def admin_settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        # FIX: Convert Rows to Dicts to prevent JSON error
        users = [dict(u) for u in conn.execute("SELECT * FROM users").fetchall()]
        lists = []
        for l in conn.execute("SELECT * FROM checklists").fetchall():
            d = dict(l)
            try: d['task_list'] = json.loads(d['tasks'])
            except: d['task_list'] = []
            
            if d['assigned_to'] == 'all': d['assigned_names'] = "Everyone"
            else:
                ids = d['assigned_to'].split(',')
                names = [u['name'] for u in users if str(u['id']) in ids]
                d['assigned_names'] = ", ".join(names)
            lists.append(d)
            
    return render_template('settings.html', theme=THEME, users=users, checklists=lists)

@app.route('/api/add_user', methods=['POST'])
def add_user():
    try:
        with get_db() as conn: conn.execute("INSERT INTO users (name, pin, role, department) VALUES (?, ?, ?, ?)", (request.form.get('name'), request.form.get('pin'), request.form.get('role'), request.form.get('department'))); conn.commit()
    except: pass
    return redirect(url_for('admin_settings'))

@app.route('/api/delete_user/<int:uid>')
def delete_user(uid):
    with get_db() as conn: conn.execute("DELETE FROM users WHERE id=?", (uid,)); conn.commit()
    return redirect(url_for('admin_settings'))

@app.route('/api/save_checklist', methods=['POST'])
def save_checklist():
    assigned = ",".join(request.form.getlist('assigned_users')) if request.form.getlist('assigned_users') else "all"
    tasks = request.form.get('tasks_json')
    with get_db() as conn:
        if request.form.get('list_id'):
            conn.execute("UPDATE checklists SET title=?, tasks=?, assigned_to=?, frequency=?, trigger_time=? WHERE id=?", (request.form.get('title'), tasks, assigned, request.form.get('frequency'), request.form.get('trigger_time'), request.form.get('list_id')))
        else:
            conn.execute("INSERT INTO checklists (title, tasks, assigned_to, frequency, trigger_time) VALUES (?, ?, ?, ?, ?)", (request.form.get('title'), tasks, assigned, request.form.get('frequency'), request.form.get('trigger_time')))
        conn.commit()
    return redirect(url_for('admin_settings'))

@app.route('/api/delete_checklist/<int:lid>')
def delete_checklist(lid):
    with get_db() as conn: conn.execute("DELETE FROM checklists WHERE id=?", (lid,)); conn.commit()
    return redirect(url_for('admin_settings'))

@app.route('/api/submit_checklist', methods=['POST'])
def submit_checklist():
    data = request.form.to_dict(); lid = data.pop('checklist_id', None)
    for k, f in request.files.items():
        if f.filename:
            n = secure_filename(f"{int(datetime.now().timestamp())}_{f.filename}")
            f.save(app.config['UPLOAD_FOLDER'] / n); data[k] = n
    with get_db() as conn: conn.execute("INSERT INTO checklist_logs (user_id, checklist_id, data, timestamp) VALUES (?, ?, ?, ?)", (session['user_id'], lid, json.dumps(data), datetime.now())); conn.commit()
    return redirect(url_for('home'))

@app.route('/api/clock', methods=['POST'])
def clock():
    d = request.get_json()
    with get_db() as conn: conn.execute("INSERT INTO attendance (user_id, action, timestamp) VALUES (?, ?, ?)", (session['user_id'], d.get('action'), datetime.now())); conn.commit()
    return jsonify({"status": "ok"})

@app.route('/admin/user_report/<int:uid>')
def user_report(uid):
    if session.get('user_role') != 'manager': return "Denied"
    with get_db() as conn:
        u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        logs = conn.execute("SELECT * FROM attendance WHERE user_id=? ORDER BY timestamp DESC LIMIT 20", (uid,)).fetchall()
        checks = conn.execute("SELECT id, title, timestamp FROM checklist_logs l JOIN checklists c ON l.checklist_id = c.id WHERE user_id=? ORDER BY timestamp DESC LIMIT 10", (uid,)).fetchall()
    return render_template('user_report.html', user_name=u['name'], user_id=uid, logs=logs, checks=checks)

# --- FIX FOR PREVIEW API ---
@app.route('/api/get_checklist_detail/<int:log_id>')
def get_detail(log_id):
    with get_db() as conn:
        row = conn.execute("SELECT c.title, c.tasks, l.data, l.timestamp FROM checklist_logs l JOIN checklists c ON l.checklist_id = c.id WHERE l.id = ?", (log_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    d = dict(row)
    try: d['task_list'] = json.loads(d['tasks']); d['answers'] = json.loads(d['data']); del d['tasks']; del d['data']
    except: return jsonify({'error': 'Data Error'}), 500
    return jsonify(d)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True, ssl_context='adhoc')
"""

# --- 2. FIXED SETTINGS TEMPLATE ---
settings_html = """<!DOCTYPE html>
<html>
<head><title>Settings</title><meta name="viewport" content="width=device-width, initial-scale=1"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"></head>
<body class="bg-light pb-5">
<nav class="navbar bg-white shadow-sm mb-4"><div class="container"><a href="/" class="btn btn-light"><i class="fa-solid fa-arrow-left"></i></a><h5 class="m-0">Configuration</h5></div></nav>
<div class="container">
    <div class="card mb-4 border-0 shadow-sm">
        <div class="card-header bg-white"><h6 class="m-0 text-primary fw-bold">STAFF</h6></div>
        <div class="card-body">
            <form action="/api/add_user" method="POST" class="row g-2 mb-3">
                <div class="col-3"><input name="name" class="form-control" placeholder="Name" required></div>
                <div class="col-2"><input name="pin" class="form-control" placeholder="PIN" required></div>
                <div class="col-3"><select name="department" class="form-select"><option>Service</option><option>Kitchen</option><option>Admin</option></select></div>
                <div class="col-3"><select name="role" class="form-select"><option value="staff">Staff</option><option value="manager">Manager</option></select></div>
                <div class="col-1"><button class="btn btn-success w-100">+</button></div>
            </form>
            <table class="table table-sm">
                <thead><tr><th>Name</th><th>Dept</th><th>Role</th><th></th></tr></thead>
                <tbody>{% for u in users %}<tr><td>{{ u.name }}</td><td>{{ u.department }}</td><td>{{ u.role }}</td><td class="text-end"><a href="/api/delete_user/{{ u.id }}" class="text-danger"><i class="fa-solid fa-trash"></i></a></td></tr>{% endfor %}</tbody>
            </table>
        </div>
    </div>

    <div class="card border-0 shadow-sm">
        <div class="card-header bg-white"><h6 class="m-0 text-primary fw-bold">CHECKLISTS</h6></div>
        <div class="card-body">
            <form action="/api/save_checklist" method="POST" id="cForm">
                <input type="hidden" name="list_id" id="lid">
                <div class="row g-2 mb-2">
                    <div class="col-5"><input name="title" id="lt" class="form-control" placeholder="Title" required></div>
                    <div class="col-3"><select name="frequency" id="lf" class="form-select"><option>Daily</option><option>Weekly</option><option>Event</option></select></div>
                    <div class="col-2"><input type="time" name="trigger_time" id="ltime" class="form-control"></div>
                    <div class="col-2"><button class="btn btn-primary w-100 fw-bold" id="sBtn">SAVE</button></div>
                </div>
                
                <div class="input-group mb-2">
                    <input id="nt" class="form-control" placeholder="Task...">
                    <div class="input-group-text"><input type="checkbox" id="np"> <small>Photo</small></div>
                    <button type="button" class="btn btn-dark" onclick="addT()">Add</button>
                </div>
                <div id="tList" class="mb-3"></div>
                <input type="hidden" name="tasks_json" id="tJson">

                <div class="card bg-light border p-2">
                    <div class="d-flex justify-content-between mb-2"><small class="fw-bold">ASSIGN TO:</small><div><button type="button" class="btn btn-xs btn-outline-secondary" onclick="fil('Kitchen')">Kitchen</button> <button type="button" class="btn btn-xs btn-outline-secondary" onclick="fil('Service')">Service</button></div></div>
                    <div style="max-height:100px;overflow-y:auto">
                        {% for u in users %}<label class="d-flex gap-2 u-row" data-d="{{ u.department }}"><input type="checkbox" name="assigned_users" value="{{ u.id }}"> {{ u.name }}</label>{% endfor %}
                    </div>
                </div>
            </form>

            <ul class="list-group mt-4">
                {% for c in checklists %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <div><strong>{{ c.title }}</strong> <small class="text-muted">{{ c.assigned_names }}</small></div>
                    <div>
                        <button type="button" class="btn btn-sm btn-light text-success" onclick='edit({{ c|tojson }})'><i class="fa-solid fa-pen"></i></button>
                        <a href="/api/delete_checklist/{{ c.id }}" class="btn btn-sm btn-light text-danger"><i class="fa-solid fa-trash"></i></a>
                    </div>
                </li>
                {% endfor %}
            </ul>
        </div>
    </div>
</div>
<script>
    let tasks = [];
    function addT() {
        const t = document.getElementById('nt').value;
        const p = document.getElementById('np').checked;
        if(t) { tasks.push({text:t, photo:p}); render(); document.getElementById('nt').value=''; }
    }
    function render() {
        const c = document.getElementById('tList'); c.innerHTML='';
        tasks.forEach((t,i) => c.innerHTML += `<div class="badge bg-white text-dark border me-1 mb-1">${t.text} ${t.photo?'📷':''} <span class="text-danger" style="cursor:pointer" onclick="del(${i})">&times;</span></div>`);
        document.getElementById('tJson').value = JSON.stringify(tasks);
    }
    function del(i) { tasks.splice(i,1); render(); }
    function fil(d) { document.querySelectorAll('.u-row').forEach(r => { 
        const cb = r.querySelector('input'); 
        if(r.dataset.d === d) cb.checked = true; 
    }); }
    function edit(d) {
        document.getElementById('lid').value = d.id;
        document.getElementById('lt').value = d.title;
        document.getElementById('lf').value = d.frequency;
        document.getElementById('ltime').value = d.trigger_time || '';
        tasks = d.task_list; render();
        document.getElementById('sBtn').innerText = "UPDATE";
    }
</script>
</body></html>"""

# --- 3. WRITE FILES ---
os.makedirs('templates', exist_ok=True)
with open('app.py', 'w') as f: f.write(app_code)
with open('templates/settings.html', 'w') as f: f.write(settings_html)

print("✅ REPAIR COMPLETE. Database Rows fixed. Admin Stats fixed.")
print("👉 Run: python3 app.py")