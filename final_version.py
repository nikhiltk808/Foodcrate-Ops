import os

# ==========================================
# 1. APP.PY (Backend Logic)
# ==========================================
app_code = """from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import json
import os
from datetime import datetime
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
    'primary': '#4361ee', 'secondary': '#3f37c9', 'success': '#4cc9f0', 
    'warning': '#f72585', 'bg': '#f8f9fa', 'card': '#ffffff'
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Staff ID removed. Name + PIN is the login.
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, pin TEXT, role TEXT, department TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS checklist_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, checklist_id INTEGER, data TEXT, photo_path TEXT, timestamp DATETIME, edit_history TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS checklists (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, tasks TEXT, assigned_to TEXT, trigger_time TEXT, frequency TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, timestamp DATETIME)")
        
        # Default Admin
        try: conn.execute("INSERT INTO users (name, pin, role, department) VALUES ('Admin', '1234', 'manager', 'Admin')")
        except sqlite3.IntegrityError: pass

# --- ROUTES ---
@app.route('/')
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard_admin.html', theme=THEME, user=session['user_name']) if session.get('user_role') == 'manager' else redirect(url_for('staff_dashboard'))

@app.route('/staff_dashboard')
def staff_dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        # Logic to fetch assigned checklists
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
        name = request.form.get('name')
        pin = request.form.get('pin')
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

# --- SETTINGS & API ---
@app.route('/admin/settings')
def admin_settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db() as conn:
        users = [dict(u) for u in conn.execute("SELECT * FROM users").fetchall()]
        lists_raw = conn.execute("SELECT * FROM checklists").fetchall()
        
        checklists = []
        for l in lists_raw:
            d = dict(l)
            # Parse tasks for preview
            try: d['task_list'] = json.loads(d['tasks'])
            except: d['task_list'] = []
            
            # Format Assigned Names
            if d['assigned_to'] == 'all': d['assigned_names'] = "Everyone"
            else:
                ids = d['assigned_to'].split(',')
                names = [u['name'] for u in users if str(u['id']) in ids]
                d['assigned_names'] = ", ".join(names)
            checklists.append(d)
            
    return render_template('settings.html', theme=THEME, users=users, checklists=checklists)

@app.route('/api/add_user', methods=['POST'])
def add_user():
    try:
        with get_db() as conn: 
            conn.execute("INSERT INTO users (name, pin, role, department) VALUES (?, ?, ?, ?)", 
                         (request.form.get('name'), request.form.get('pin'), request.form.get('role'), request.form.get('department')))
            conn.commit()
    except: pass
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

@app.route('/api/delete_user/<int:uid>')
def delete_user(uid):
    with get_db() as conn: conn.execute("DELETE FROM users WHERE id=?", (uid,)); conn.commit()
    return redirect(url_for('admin_settings'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True, ssl_context='adhoc')
"""

# ==========================================
# 2. SETTINGS.HTML (The New UI)
# ==========================================
settings_html = """<!DOCTYPE html>
<html>
<head>
    <title>Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background: #f8f9fa; font-family: 'Segoe UI', sans-serif; padding-bottom: 50px; }
        .navbar { background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .card { border: none; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); margin-bottom: 20px; }
        .form-label { font-weight: 700; font-size: 0.75rem; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; }
        .btn-action { width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; border-radius: 6px; transition: 0.2s; border: none; }
        .btn-action:hover { transform: scale(1.1); }
        .dept-tag { font-size: 0.7em; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; }
        
        /* Task Builder Styles */
        .task-row { background: #fff; border: 1px solid #eee; padding: 8px 12px; margin-bottom: 5px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }
        .photo-req { color: #f72585; font-size: 0.8rem; font-weight: bold; }
    </style>
</head>
<body>

<nav class="navbar mb-4 py-3">
    <div class="container">
        <div class="d-flex align-items-center">
            <a href="/" class="btn btn-light me-3"><i class="fa-solid fa-arrow-left"></i></a>
            <h5 class="fw-bold m-0 text-dark">System Configuration</h5>
        </div>
    </div>
</nav>

<div class="container">
    
    <div class="card">
        <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#staffPanel" style="cursor:pointer">
            <h6 class="fw-bold m-0 text-primary"><i class="fa-solid fa-user-group me-2"></i> STAFF MANAGEMENT</h6>
            <i class="fa-solid fa-chevron-down text-muted"></i>
        </div>
        <div id="staffPanel" class="collapse">
            <div class="card-body bg-light">
                <form action="/api/add_user" method="POST" class="row g-2 align-items-end mb-4">
                    <div class="col-md-3">
                        <label class="form-label">Name</label>
                        <input name="name" class="form-control" placeholder="e.g. Chef Mike" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">PIN</label>
                        <input name="pin" class="form-control" placeholder="****" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Department</label>
                        <select name="department" class="form-select">
                            <option value="Service">Service Team</option>
                            <option value="Kitchen">Kitchen Team</option>
                            <option value="Admin">Admin</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Role</label>
                        <select name="role" class="form-select">
                            <option value="staff">Staff</option>
                            <option value="manager">Manager</option>
                        </select>
                    </div>
                    <div class="col-md-1">
                        <button class="btn btn-success w-100"><i class="fa-solid fa-plus"></i></button>
                    </div>
                </form>

                <div class="bg-white rounded border p-0">
                    <table class="table table-hover mb-0 align-middle">
                        <thead class="table-light"><tr><th class="ps-3">Name</th><th>PIN</th><th>Dept</th><th>Role</th><th class="text-end pe-3">Action</th></tr></thead>
                        <tbody>
                            {% for u in users %}
                            <tr>
                                <td class="ps-3 fw-bold">{{ u.name }}</td>
                                <td class="text-muted">****</td>
                                <td><span class="dept-tag {{ 'bg-warning text-dark' if u.department=='Kitchen' else 'bg-info text-white' }}">{{ u.department }}</span></td>
                                <td>{{ u.role }}</td>
                                <td class="text-end pe-3">
                                    {% if u.role != 'manager' %}
                                    <a href="/api/delete_user/{{ u.id }}" class="text-danger small"><i class="fa-solid fa-trash"></i></a>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <div class="card h-100">
        <div class="card-header bg-white py-3">
            <h6 class="fw-bold m-0 text-primary"><i class="fa-solid fa-list-check me-2"></i> CHECKLIST MANAGER</h6>
        </div>
        <div class="card-body">
            
            <form action="/api/save_checklist" method="POST" id="checklistForm" class="p-3 bg-light rounded-3 mb-4 border">
                <input type="hidden" name="list_id" id="list_id">
                <div class="d-flex justify-content-between mb-3">
                    <h6 class="fw-bold text-muted m-0" id="formTitle">CREATE NEW CHECKLIST</h6>
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="resetForm()" id="resetBtn" style="display:none;">Cancel</button>
                </div>
                
                <div class="row g-2 mb-3">
                    <div class="col-md-5">
                        <input name="title" id="title" class="form-control" placeholder="Checklist Title" required>
                    </div>
                    <div class="col-md-3">
                        <select name="frequency" id="frequency" class="form-select">
                            <option value="Daily">Daily</option>
                            <option value="Weekly">Weekly</option>
                            <option value="Monthly">Monthly</option>
                            <option value="Event">Event</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <input type="time" name="trigger_time" id="trigger_time" class="form-control">
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-primary w-100 fw-bold" id="saveBtn">SAVE</button>
                    </div>
                </div>

                <label class="form-label">Add Tasks</label>
                <div class="input-group mb-3">
                    <input type="text" id="newTask" class="form-control" placeholder="e.g. Clean the Deep Fryer">
                    <div class="input-group-text bg-white">
                        <input class="form-check-input mt-0 me-2" type="checkbox" id="reqPhoto"> 
                        <small class="fw-bold"><i class="fa-solid fa-camera"></i> Photo Req.</small>
                    </div>
                    <button type="button" class="btn btn-dark" onclick="addTask()">Add Task</button>
                </div>
                
                <div id="taskListDisplay" class="mb-3"></div>
                <input type="hidden" name="tasks_json" id="tasks_json">

                <div class="card border bg-white mt-3">
                    <div class="card-header bg-white py-2 d-flex justify-content-between align-items-center">
                        <span class="fw-bold small text-muted">ASSIGN TO:</span>
                        <div class="btn-group btn-group-sm">
                            <button type="button" class="btn btn-outline-secondary" onclick="filterStaff('all')">Show All</button>
                            <button type="button" class="btn btn-outline-warning" onclick="filterStaff('Kitchen')">Kitchen Only</button>
                            <button type="button" class="btn btn-outline-info" onclick="filterStaff('Service')">Service Only</button>
                        </div>
                    </div>
                    <div class="card-body p-0" style="max-height: 150px; overflow-y: auto;">
                        <div class="list-group list-group-flush">
                            {% for u in users %}
                            <label class="list-group-item d-flex gap-3 align-items-center staff-checkbox-item" data-dept="{{ u.department }}">
                                <input class="form-check-input flex-shrink-0 staff-check" type="checkbox" name="assigned_users" value="{{ u.id }}">
                                <div class="d-flex justify-content-between w-100">
                                    <span>{{ u.name }}</span>
                                    <span class="dept-tag {{ 'bg-warning text-dark' if u.department=='Kitchen' else 'bg-info text-white' }}">{{ u.department }}</span>
                                </div>
                            </label>
                            {% endfor %}
                        </div>
                    </div>
                    <div class="card-footer bg-light p-1 text-center">
                        <button type="button" class="btn btn-sm btn-link text-decoration-none" onclick="selectAllVisible()">Select All Visible</button>
                    </div>
                </div>
            </form>

            <h6 class="fw-bold text-muted ps-2 mb-3 mt-4">ACTIVE CHECKLISTS</h6>
            <div class="list-group">
                {% for c in checklists %}
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <div class="fw-bold text-dark">{{ c.title }}</div>
                        <div class="small text-muted">
                            <span class="badge bg-light text-dark border me-1">{{ c.frequency }}</span>
                            <i class="fa-solid fa-users me-1"></i> {{ c.assigned_names }}
                        </div>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="button" class="btn-action bg-light text-primary" onclick='showPreview({{ c|tojson }})'><i class="fa-solid fa-eye"></i></button>
                        <button type="button" class="btn-action bg-light text-success" onclick='editList({{ c|tojson }})'><i class="fa-solid fa-pen"></i></button>
                        <a href="/api/delete_checklist/{{ c.id }}" class="btn-action bg-light text-danger" onclick="return confirm('Delete?')"><i class="fa-solid fa-trash"></i></a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="previewModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header bg-light">
        <h5 class="modal-title fw-bold" id="pTitle"></h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <div class="mb-3 text-muted small"><i class="fa-solid fa-users"></i> Assigned: <span id="pAssigned" class="fw-bold text-dark"></span></div>
        <ul class="list-group list-group-flush" id="pList"></ul>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    let currentTasks = [];

    // --- TASK BUILDER ---
    function addTask() {
        const txt = document.getElementById('newTask').value;
        const photo = document.getElementById('reqPhoto').checked;
        if(!txt) return;
        currentTasks.push({text: txt, photo: photo});
        renderTasks();
        document.getElementById('newTask').value = '';
        document.getElementById('reqPhoto').checked = false;
    }

    function renderTasks() {
        const container = document.getElementById('taskListDisplay');
        container.innerHTML = '';
        currentTasks.forEach((t, i) => {
            container.innerHTML += `
            <div class="task-row">
                <span>${t.text} ${t.photo ? '<span class="photo-req ms-2"><i class="fa-solid fa-camera"></i> REQ</span>' : ''}</span>
                <span class="text-danger" style="cursor:pointer" onclick="removeTask(${i})">&times;</span>
            </div>`;
        });
        document.getElementById('tasks_json').value = JSON.stringify(currentTasks);
    }

    function removeTask(i) {
        currentTasks.splice(i, 1);
        renderTasks();
    }

    // --- ASSIGNMENT LOGIC ---
    function filterStaff(dept) {
        const rows = document.querySelectorAll('.staff-checkbox-item');
        rows.forEach(row => {
            if (dept === 'all' || row.getAttribute('data-dept') === dept) {
                row.style.display = 'flex';
            } else {
                row.style.display = 'none';
                row.querySelector('input').checked = false; // Auto uncheck hidden
            }
        });
    }

    function selectAllVisible() {
        document.querySelectorAll('.staff-checkbox-item').forEach(row => {
            if (row.style.display !== 'none') row.querySelector('input').checked = true;
        });
    }

    // --- EDIT & PREVIEW ---
    function editList(data) {
        document.getElementById('list_id').value = data.id;
        document.getElementById('title').value = data.title;
        document.getElementById('frequency').value = data.frequency;
        document.getElementById('trigger_time').value = data.trigger_time || '';
        
        // Parse tasks correctly
        currentTasks = data.task_list;
        renderTasks();
        
        document.getElementById('formTitle').innerText = "EDITING: " + data.title;
        document.getElementById('saveBtn').innerText = "UPDATE";
        document.getElementById('resetBtn').style.display = 'block';
        document.getElementById('checklistForm').scrollIntoView({behavior: 'smooth'});
    }

    function showPreview(data) {
        document.getElementById('pTitle').innerText = data.title;
        document.getElementById('pAssigned').innerText = data.assigned_names;
        const list = document.getElementById('pList');
        list.innerHTML = '';
        
        data.task_list.forEach(t => {
            list.innerHTML += `
            <li class="list-group-item d-flex justify-content-between align-items-center">
                <span><i class="fa-regular fa-square me-2"></i> ${t.text}</span>
                ${t.photo ? '<span class="badge bg-warning text-dark"><i class="fa-solid fa-camera"></i></span>' : ''}
            </li>`;
        });
        new bootstrap.Modal(document.getElementById('previewModal')).show();
    }

    function resetForm() {
        document.getElementById('checklistForm').reset();
        document.getElementById('list_id').value = '';
        currentTasks = [];
        renderTasks();
        document.getElementById('formTitle').innerText = "NEW CHECKLIST";
        document.getElementById('saveBtn').innerText = "SAVE";
        document.getElementById('resetBtn').style.display = 'none';
    }
</script>
</body>
</html>"""

# ==========================================
# 3. WRITE FILES
# ==========================================
os.makedirs('templates', exist_ok=True)

with open('app.py', 'w') as f:
    f.write(app_code)
    print("✅ Created app.py")

with open('templates/settings.html', 'w') as f:
    f.write(settings_html)
    print("✅ Created templates/settings.html")

print("\\n🚀 UPDATE COMPLETE")
print("1. DELETE 'zion_ops.db' (Crucial!)")
print("2. RESTART server: python3 app.py")
print("3. LOGIN: Admin / 1234")