import os

# ==========================================
# 1. APP.PY (The Stable, Crash-Proof Backend)
# ==========================================
app_code = """from flask import Flask, render_template, request, jsonify, session, redirect, url_for
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

# --- THEME (Modern Blue) ---
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
        # Default Admin: Name 'Admin', PIN '1234'
        try: conn.execute("INSERT INTO users (name, pin, role, department) VALUES ('Admin', '1234', 'manager', 'Admin')")
        except sqlite3.IntegrityError: pass

# --- ANALYTICS (Calculated in Python to prevent Crash) ---
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
                
                # Timeline Math
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
        data = get_admin_stats(session.get('user_dept'))
        return render_template('dashboard_admin.html', theme=THEME, user=session['user_name'], data=data, dept=session.get('user_dept'))
    return redirect(url_for('staff_dashboard'))

@app.route('/staff_dashboard')
def staff_dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        all_lists = conn.execute("SELECT * FROM checklists").fetchall()
        my_lists = []
        for row in all_lists:
            r = dict(row)
            try: r['task_items'] = json.loads(r['tasks']) 
            except: r['task_items'] = []
            assigned_ids = r['assigned_to'].split(',') if r['assigned_to'] else []
            if (r['assigned_to'] == 'all') or (str(session['user_id']) in assigned_ids): my_lists.append(r)
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
            else: return render_template('login.html', theme=THEME, error="Invalid Name or PIN")
    return render_template('login.html', theme=THEME)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

# --- ADMIN API ---
@app.route('/admin/settings')
def admin_settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        users = [dict(u) for u in conn.execute("SELECT * FROM users").fetchall()]
        lists = []
        for l in conn.execute("SELECT * FROM checklists").fetchall():
            d = dict(l)
            if d['assigned_to'] == 'all': d['assigned_names'] = "Everyone"
            else:
                ids = d['assigned_to'].split(',')
                names = [u['name'] for u in users if str(u['id']) in ids]
                d['assigned_names'] = ", ".join(names)
            try: d['task_list'] = json.loads(d['tasks'])
            except: d['task_list'] = []
            lists.append(d)
    return render_template('settings.html', theme=THEME, users=users, checklists=lists)

@app.route('/api/add_user', methods=['POST'])
def add_user():
    try:
        with get_db() as conn: 
            conn.execute("INSERT INTO users (name, pin, role, department) VALUES (?, ?, ?, ?)", 
                         (request.form.get('name'), request.form.get('pin'), request.form.get('role'), request.form.get('department')))
            conn.commit()
    except: pass
    return redirect(url_for('admin_settings'))

@app.route('/api/delete_user/<int:uid>')
def delete_user(uid):
    with get_db() as conn: conn.execute("DELETE FROM users WHERE id=?", (uid,)); conn.commit()
    return redirect(url_for('admin_settings'))

@app.route('/api/save_checklist', methods=['POST'])
def save_checklist():
    assigned = ",".join(request.form.getlist('assigned_users')) if request.form.getlist('assigned_users') else "all"
    tasks_json = request.form.get('tasks_json')
    
    with get_db() as conn:
        if request.form.get('list_id'):
            conn.execute("UPDATE checklists SET title=?, tasks=?, assigned_to=?, frequency=?, trigger_time=? WHERE id=?", 
                         (request.form.get('title'), tasks_json, assigned, request.form.get('frequency'), request.form.get('trigger_time'), request.form.get('list_id')))
        else:
            conn.execute("INSERT INTO checklists (title, tasks, assigned_to, frequency, trigger_time) VALUES (?, ?, ?, ?, ?)", 
                         (request.form.get('title'), tasks_json, assigned, request.form.get('frequency'), request.form.get('trigger_time')))
        conn.commit()
    return redirect(url_for('admin_settings'))

@app.route('/api/delete_checklist/<int:lid>')
def delete_checklist(lid):
    with get_db() as conn: conn.execute("DELETE FROM checklists WHERE id=?", (lid,)); conn.commit()
    return redirect(url_for('admin_settings'))

@app.route('/api/submit_checklist', methods=['POST'])
def submit_checklist():
    form_data = request.form.to_dict(); checklist_id = form_data.pop('checklist_id', None)
    # Save files
    for key, file in request.files.items():
        if file.filename:
            fname = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
            file.save(app.config['UPLOAD_FOLDER'] / fname)
            form_data[key] = fname
            
    with get_db() as conn:
        conn.execute("INSERT INTO checklist_logs (user_id, checklist_id, data, timestamp) VALUES (?, ?, ?, ?)", 
                     (session['user_id'], checklist_id, json.dumps(form_data), datetime.now()))
        conn.commit()
    return redirect(url_for('home'))

@app.route('/api/clock', methods=['POST'])
def clock_action():
    data = request.get_json()
    with get_db() as conn: conn.execute("INSERT INTO attendance (user_id, action, timestamp) VALUES (?, ?, ?)", (session['user_id'], data.get('action'), datetime.now())); conn.commit()
    return jsonify({"status": "success"})

@app.route('/api/quick_assign', methods=['POST'])
def quick_assign():
    tasks = json.dumps([{"text": request.form.get('task_title'), "photo": False}])
    with get_db() as conn:
        conn.execute("INSERT INTO checklists (title, tasks, assigned_to, trigger_time, frequency) VALUES (?, ?, ?, ?, 'Event')", 
                     ("⚡ " + request.form.get('task_title'), tasks, request.form.get('assign_to'), datetime.now().strftime("%H:%M")))
        conn.commit()
    return redirect(url_for('home'))

@app.route('/admin/user_report/<int:user_id>')
def user_report(user_id):
    if session.get('user_role') != 'manager': return "Denied"
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        logs = conn.execute("SELECT * FROM attendance WHERE user_id=? ORDER BY timestamp DESC LIMIT 20", (user_id,)).fetchall()
        checks = conn.execute("SELECT id, title, timestamp FROM checklist_logs l JOIN checklists c ON l.checklist_id = c.id WHERE user_id=? ORDER BY timestamp DESC LIMIT 10", (user_id,)).fetchall()
    return render_template('user_report.html', user_name=user['name'], user_id=user_id, logs=logs, checks=checks)

# --- CHECKLIST DETAIL API (Fixes Eye Button) ---
@app.route('/api/get_checklist_detail/<int:log_id>')
def get_checklist_detail(log_id):
    with get_db() as conn:
        row = conn.execute("SELECT c.title, c.tasks, l.data, l.timestamp FROM checklist_logs l JOIN checklists c ON l.checklist_id = c.id WHERE l.id = ?", (log_id,)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    data = dict(row)
    try:
        data['task_list'] = json.loads(data['tasks'])
        data['answers'] = json.loads(data['data'])
        del data['tasks']; del data['data']
    except: return jsonify({'error': 'Data Error'}), 500
    return jsonify(data)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True, ssl_context='adhoc')
"""

# ==========================================
# 2. LOGIN (Clean & Simple)
# ==========================================
login_html = """<!DOCTYPE html>
<html>
<head>
    <title>Zion Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{background:#4F46E5;height:100vh;display:flex;align-items:center;justify-content:center}.card{width:100%;max-width:350px;padding:30px;border-radius:15px;}</style>
</head>
<body>
    <div class="card">
        <h3 class="text-center fw-bold mb-4" style="color:#4F46E5">Login</h3>
        {% if error %}<div class="alert alert-danger p-2 text-center small mb-3">{{ error }}</div>{% endif %}
        <form method="POST" action="/login">
            <div class="mb-3"><label class="fw-bold small text-muted">NAME</label><input name="name" class="form-control" placeholder="e.g. Admin" required></div>
            <div class="mb-4"><label class="fw-bold small text-muted">PIN</label><input type="password" name="pin" class="form-control" placeholder="****" required></div>
            <button class="btn btn-primary w-100 fw-bold">Login</button>
        </form>
    </div>
</body>
</html>"""

# ==========================================
# 3. ADMIN DASHBOARD (Modern & Stats)
# ==========================================
admin_html = """<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #F8FAFC; font-family: system-ui; padding: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .stat-val { font-size: 2rem; font-weight: 700; color: #1e293b; }
        .timeline-row { background: white; margin-bottom: 10px; padding: 15px; border-radius: 10px; display: flex; align-items: center; border-left: 4px solid #cbd5e1; }
        .status-IN { border-left-color: #10B981; }
        .timeline-bar { height: 8px; background: #4F46E5; border-radius: 4px; position: absolute; }
    </style>
</head>
<body>
    <div class="d-flex justify-content-between mb-4">
        <h3>Welcome, {{ user }}</h3>
        <div><a href="/admin/settings" class="btn btn-outline-dark me-2">Settings</a><a href="/logout" class="btn btn-danger">Exit</a></div>
    </div>

    <div class="row g-3 mb-4">
        <div class="col-md-3"><div class="stat-card"><div>Active</div><div class="stat-val text-success">{{ data.present }}</div></div></div>
        <div class="col-md-3"><div class="stat-card"><div>Late</div><div class="stat-val text-warning">{{ data.late }}</div></div></div>
        <div class="col-md-3"><div class="stat-card"><div>Total Team</div><div class="stat-val">{{ data.total }}</div></div></div>
        <div class="col-md-3"><div class="stat-card bg-primary text-white"><div>Top Star</div><div class="h4 mt-2">{{ data.top_star.name if data.top_star else 'No Data' }}</div></div></div>
    </div>

    <div class="card p-3 mb-4 border-0 shadow-sm">
        <form action="/api/quick_assign" method="POST" class="row g-2 align-items-center">
            <div class="col-auto fw-bold">⚡ Quick Task:</div>
            <div class="col"><input name="task_title" class="form-control" placeholder="e.g. Clean Spill" required></div>
            <div class="col-auto">
                <select name="assign_to" class="form-select">
                    <option value="all">Everyone</option>
                    {% for s in data.staff %}<option value="{{ s.id }}">{{ s.name }}</option>{% endfor %}
                </select>
            </div>
            <div class="col-auto"><button class="btn btn-dark">Assign</button></div>
        </form>
    </div>

    <h6 class="text-muted mb-3">LIVE TIMELINE</h6>
    {% for s in data.staff %}
    <div class="timeline-row status-{{ s.status }}" onclick="location.href='/admin/user_report/{{ s.id }}'" style="cursor:pointer">
        <div style="width: 200px;"><strong>{{ s.name }}</strong><br><small class="text-muted">{{ s.dept }}</small></div>
        <div style="flex-grow: 1; height: 8px; background: #eee; border-radius: 4px; position: relative;">
            <div class="timeline-bar" style="left: {{ s.bar_left }}%; width: {{ s.bar_width }}%;"></div>
        </div>
        <div style="width: 100px; text-align: right;">{{ s.start }}</div>
    </div>
    {% endfor %}
</body>
</html>"""

# ==========================================
# 4. SETTINGS (Smart Assignment + Task Builder)
# ==========================================
settings_html = """<!DOCTYPE html>
<html>
<head>
    <title>Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f8f9fa; padding: 20px; }
        .card { border: none; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
        .staff-item:hover { background: #f1f5f9; }
    </style>
</head>
<body>
<nav class="mb-4"><a href="/" class="btn btn-outline-secondary">← Back to Dashboard</a></nav>

<div class="row">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header bg-white d-flex justify-content-between" data-bs-toggle="collapse" data-bs-target="#staffBox" style="cursor:pointer">
                <h6 class="m-0 fw-bold text-primary">STAFF MANAGEMENT</h6><span>▼</span>
            </div>
            <div id="staffBox" class="collapse show">
                <div class="card-body">
                    <form action="/api/add_user" method="POST" class="row g-2 mb-3">
                        <div class="col-3"><input name="name" class="form-control" placeholder="Name" required></div>
                        <div class="col-2"><input name="pin" class="form-control" placeholder="PIN" required></div>
                        <div class="col-3"><select name="department" class="form-select"><option>Service</option><option>Kitchen</option><option>Admin</option></select></div>
                        <div class="col-3"><select name="role" class="form-select"><option value="staff">Staff</option><option value="manager">Manager</option></select></div>
                        <div class="col-1"><button class="btn btn-success w-100">+</button></div>
                    </form>
                    <table class="table table-sm">
                        {% for u in users %}
                        <tr><td>{{ u.name }}</td><td>{{ u.department }}</td><td>{{ u.role }}</td><td class="text-end"><a href="/api/delete_user/{{ u.id }}" class="text-danger">Del</a></td></tr>
                        {% endfor %}
                    </table>
                </div>
            </div>
        </div>
    </div>

    <div class="col-md-12">
        <div class="card">
            <div class="card-header bg-white"><h6 class="m-0 fw-bold text-primary">CHECKLIST CREATOR</h6></div>
            <div class="card-body">
                <form action="/api/save_checklist" method="POST">
                    <div class="row g-2 mb-3">
                        <div class="col-5"><input name="title" class="form-control" placeholder="Checklist Title" required></div>
                        <div class="col-3"><select name="frequency" class="form-select"><option>Daily</option><option>Weekly</option><option>Event</option></select></div>
                        <div class="col-2"><input type="time" name="trigger_time" class="form-control"></div>
                        <div class="col-2"><button class="btn btn-primary w-100 fw-bold">SAVE</button></div>
                    </div>

                    <div class="input-group mb-2">
                        <input id="nt" class="form-control" placeholder="New Task...">
                        <div class="input-group-text"><input type="checkbox" id="np"> Photo?</div>
                        <button type="button" class="btn btn-dark" onclick="addTask()">Add</button>
                    </div>
                    <div id="tList" class="mb-3"></div>
                    <input type="hidden" name="tasks_json" id="tJson">

                    <div class="card bg-light border p-2">
                        <div class="d-flex justify-content-between mb-2">
                            <small class="fw-bold">ASSIGN TO:</small>
                            <div>
                                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="fil('all')">All</button>
                                <button type="button" class="btn btn-sm btn-outline-warning" onclick="fil('Kitchen')">Kitchen</button>
                                <button type="button" class="btn btn-sm btn-outline-info" onclick="fil('Service')">Service</button>
                            </div>
                        </div>
                        <div style="max-height:150px;overflow-y:auto">
                            {% for u in users %}
                            <label class="d-flex gap-2 staff-item p-1 rounded" data-dept="{{ u.department }}">
                                <input type="checkbox" name="assigned_users" value="{{ u.id }}"> {{ u.name }} <span class="badge bg-light text-dark border">{{ u.department }}</span>
                            </label>
                            {% endfor %}
                        </div>
                    </div>
                </form>

                <ul class="list-group mt-3">
                    {% for c in checklists %}
                    <li class="list-group-item d-flex justify-content-between">
                        <div><strong>{{ c.title }}</strong> <small>({{ c.assigned_names }})</small></div>
                        <a href="/api/delete_checklist/{{ c.id }}" class="text-danger">Del</a>
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>
</div>

<script>
    let tasks = [];
    function addTask() {
        let t = document.getElementById('nt').value;
        let p = document.getElementById('np').checked;
        if(t){ tasks.push({text:t, photo:p}); render(); document.getElementById('nt').value=''; }
    }
    function render() {
        let c = document.getElementById('tList'); c.innerHTML='';
        tasks.forEach((t,i) => c.innerHTML += `<span class="badge bg-white text-dark border me-1">${t.text} ${t.photo?'📷':''} <span onclick="tasks.splice(${i},1);render()" style="cursor:pointer">&times;</span></span>`);
        document.getElementById('tJson').value = JSON.stringify(tasks);
    }
    function fil(d) {
        document.querySelectorAll('.staff-item').forEach(r => {
            let cb = r.querySelector('input');
            if(d==='all' || r.dataset.dept===d) { r.style.display='flex'; cb.checked=true; }
            else { r.style.display='none'; cb.checked=false; }
        });
    }
</script>
</body>
</html>"""

# ==========================================
# 5. USER REPORT (With Preview Eye)
# ==========================================
report_html = """<!DOCTYPE html>
<html>
<head><title>Report</title><meta name="viewport" content="width=device-width, initial-scale=1"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light p-4">
<div class="d-flex justify-content-between mb-4"><h4>{{ user_name }}</h4><a href="/" class="btn btn-secondary btn-sm">Back</a></div>

<div class="card mb-3 p-3 border-0 shadow-sm">
    <h6>Recent Shifts</h6>
    <table class="table table-sm">{% for l in logs %}<tr><td>{{l.action}}</td><td>{{l.timestamp}}</td></tr>{% endfor %}</table>
</div>

<div class="card p-3 border-0 shadow-sm">
    <h6>Checklists</h6>
    <ul class="list-group list-group-flush">
        {% for c in checks %}
        <li class="list-group-item d-flex justify-content-between">
            <div>{{c.title}} <br><small class="text-muted">{{c.timestamp}}</small></div>
            <button class="btn btn-sm btn-outline-primary" onclick="view({{c.id}})">👁️ View</button>
        </li>
        {% endfor %}
    </ul>
</div>

<div class="modal fade" id="vMod" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 id="vT"></h5><button class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body" id="vB"></div></div></div></div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    async function view(id) {
        const m = new bootstrap.Modal(document.getElementById('vMod')); m.show();
        const res = await fetch('/api/get_checklist_detail/'+id);
        const d = await res.json();
        document.getElementById('vT').innerText = d.title;
        let h = '<ul class="list-group">';
        d.task_list.forEach((t, i) => {
            const chk = d.answers['task_'+(i+1)] === 'on';
            h += `<li class="list-group-item"><input type="checkbox" ${chk?'checked':''} disabled> ${t.text}</li>`;
        });
        document.getElementById('vB').innerHTML = h+'</ul>';
    }
</script>
</body>
</html>"""

# ==========================================
# 6. WRITE FILES
# ==========================================
os.makedirs('templates', exist_ok=True)
with open('app.py', 'w') as f: f.write(app_code)
with open('templates/login.html', 'w') as f: f.write(login_html)
with open('templates/dashboard_admin.html', 'w') as f: f.write(admin_html)
with open('templates/settings.html', 'w') as f: f.write(settings_html)
with open('templates/user_report.html', 'w') as f: f.write(report_html)

# Blank Staff Dashboard (Basic)
with open('templates/dashboard_staff.html', 'w') as f: f.write("<h1>Staff Dashboard</h1>")

print("✅ RESTORE COMPLETE.")
print("1. DELETE 'zion_ops.db'")
print("2. Run 'python3 app.py'")
print("3. Login: Admin / 1234")