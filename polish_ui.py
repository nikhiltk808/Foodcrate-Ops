import os

# --- 1. PREMIUM LOGIN PAGE (Glassmorphism) ---
login_html = """<!DOCTYPE html>
<html>
<head>
    <title>Zion Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {
            background: linear-gradient(135deg, #4361ee 0%, #3a0ca3 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Poppins', sans-serif;
        }
        .login-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 50px 40px;
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        .brand-icon {
            font-size: 3rem;
            color: #4361ee;
            margin-bottom: 20px;
            background: #eef2ff;
            width: 80px; height: 80px;
            line-height: 80px;
            border-radius: 50%;
            display: inline-block;
        }
        .form-control {
            background: #f8f9fa;
            border: 2px solid #e9ecef;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 15px;
            font-weight: 500;
        }
        .form-control:focus {
            border-color: #4361ee;
            box-shadow: none;
            background: white;
        }
        .btn-login {
            background: #4361ee;
            color: white;
            padding: 12px;
            border-radius: 10px;
            font-weight: 700;
            width: 100%;
            border: none;
            transition: 0.3s;
        }
        .btn-login:hover { background: #3a0ca3; transform: translateY(-2px); }
        .label-text { text-align: left; font-size: 0.8rem; font-weight: 700; color: #6c757d; margin-bottom: 5px; display: block; text-transform: uppercase; letter-spacing: 1px; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="brand-icon"><i class="fa-solid fa-mountain-sun"></i></div>
        <h3 class="fw-bold mb-1">Welcome Back</h3>
        <p class="text-muted mb-4 small">Enter your Staff ID & PIN to access Zion Ops</p>
        
        {% if error %}
            <div class="alert alert-danger p-2 small border-0 bg-danger text-white mb-4"><i class="fa-solid fa-triangle-exclamation"></i> {{ error }}</div>
        {% endif %}

        <form method="POST" action="/login">
            <label class="label-text">Staff ID</label>
            <input type="number" name="staff_id" class="form-control" placeholder="e.g. 101" required autofocus>
            
            <label class="label-text">Security PIN</label>
            <input type="password" name="pin" class="form-control" placeholder="••••" required>
            
            <button type="submit" class="btn btn-login mt-2">ACCESS SYSTEM <i class="fa-solid fa-arrow-right ms-2"></i></button>
        </form>
    </div>
</body>
</html>"""

# --- 2. SETTINGS PAGE (Time Picker + Edit + Preview) ---
settings_html = """<!DOCTYPE html>
<html>
<head>
    <title>Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background: #f4f6f7; font-family: 'Segoe UI', sans-serif; padding-bottom: 50px; }
        .navbar { background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .card { border: none; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
        .form-label { font-weight: 700; font-size: 0.75rem; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; }
        .btn-action { width: 35px; height: 35px; display: inline-flex; align-items: center; justify-content: center; border-radius: 8px; transition: 0.2s; border: none; }
        .btn-action:hover { transform: scale(1.1); }
        .list-group-item { border: none; border-bottom: 1px solid #f1f1f1; padding: 15px; }
        .list-group-item:last-child { border-bottom: none; }
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
    <div class="row g-4">
        
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#staffBody" style="cursor:pointer">
                    <h6 class="fw-bold m-0 text-primary"><i class="fa-solid fa-users me-2"></i> STAFF MANAGEMENT</h6>
                    <i class="fa-solid fa-chevron-down text-muted"></i>
                </div>
                <div id="staffBody" class="collapse">
                    <div class="card-body">
                        <form action="/api/add_user" method="POST" class="row g-2 mb-4">
                            <div class="col-md-2"><input name="staff_id" class="form-control" placeholder="ID" required></div>
                            <div class="col-md-2"><input name="pin" class="form-control" placeholder="PIN" required></div>
                            <div class="col-md-3"><input name="name" class="form-control" placeholder="Name" required></div>
                            <div class="col-md-2"><select name="department" class="form-select"><option>Service</option><option>Kitchen</option><option>Admin</option></select></div>
                            <div class="col-md-2"><select name="role" class="form-select"><option value="staff">Staff</option><option value="manager">Manager</option></select></div>
                            <div class="col-md-1"><button class="btn btn-success w-100"><i class="fa-solid fa-plus"></i></button></div>
                        </form>
                        <div class="table-responsive">
                            <table class="table table-sm align-middle">
                                <thead class="table-light"><tr><th>ID</th><th>Name</th><th>Dept</th><th>Role</th><th></th></tr></thead>
                                <tbody>
                                    {% for u in users %}
                                    <tr>
                                        <td><span class="badge bg-light text-dark">{{ u.staff_id }}</span></td>
                                        <td class="fw-bold">{{ u.name }}</td>
                                        <td>{{ u.department }}</td>
                                        <td>{{ u.role }}</td>
                                        <td class="text-end">{% if u.staff_id != '999' %}<a href="/api/delete_user/{{ u.id }}" class="text-danger"><i class="fa-solid fa-trash"></i></a>{% endif %}</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-md-12">
            <div class="card h-100">
                <div class="card-header bg-white py-3 border-bottom">
                    <h6 class="fw-bold m-0 text-primary"><i class="fa-solid fa-list-check me-2"></i> CHECKLIST EDITOR</h6>
                </div>
                <div class="card-body">
                    
                    <form action="/api/save_checklist" method="POST" id="checklistForm" class="p-3 bg-light rounded-3 mb-4 border">
                        <input type="hidden" name="list_id" id="list_id">
                        <div class="d-flex justify-content-between mb-3">
                            <h6 class="fw-bold text-muted m-0" id="formTitle">CREATE NEW CHECKLIST</h6>
                            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="resetForm()" id="resetBtn" style="display:none;">Cancel Edit</button>
                        </div>
                        
                        <div class="row g-3">
                            <div class="col-md-5">
                                <label class="form-label">Title</label>
                                <input name="title" id="title" class="form-control" placeholder="e.g. Morning Prep" required>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label">Type / Frequency</label>
                                <select name="frequency" id="frequency" class="form-select">
                                    <option value="Daily">Daily Routine</option>
                                    <option value="Weekly">Weekly Deep Clean</option>
                                    <option value="Monthly">Monthly Inventory</option>
                                    <option value="Event">Event Specific</option>
                                </select>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label">Trigger Time</label>
                                <input type="time" name="trigger_time" id="trigger_time" class="form-control">
                            </div>
                            <div class="col-md-2 d-flex align-items-end">
                                <button class="btn btn-primary w-100 fw-bold" id="saveBtn"><i class="fa-solid fa-save"></i> SAVE</button>
                            </div>
                            <div class="col-12">
                                <label class="form-label">Tasks (JSON Format)</label>
                                <textarea name="tasks" id="tasks" class="form-control font-monospace" rows="2" placeholder='["Check temp", "Wipe counters"]' required></textarea>
                                <div class="form-text small">Enter tasks as a list: ["Task 1", "Task 2"]</div>
                            </div>
                        </div>
                    </form>

                    <h6 class="fw-bold text-muted ps-2 mb-3">ACTIVE CHECKLISTS</h6>
                    <ul class="list-group">
                        {% for c in checklists %}
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-bold text-dark mb-1">{{ c.title }}</div>
                                <div>
                                    <span class="badge bg-secondary me-2">{{ c.frequency }}</span>
                                    {% if c.trigger_time %}<span class="badge bg-warning text-dark"><i class="fa-regular fa-clock"></i> {{ c.trigger_time }}</span>{% endif %}
                                </div>
                            </div>
                            <div class="d-flex gap-2">
                                <button type="button" class="btn-action bg-light text-primary" 
                                        onclick="showPreview('{{ c.title }}', '{{ c.tasks_str }}')">
                                    <i class="fa-solid fa-eye"></i>
                                </button>
                                
                                <button type="button" class="btn-action bg-light text-success" 
                                        onclick='editList({{ c|tojson }})'>
                                    <i class="fa-solid fa-pen"></i>
                                </button>
                                
                                <a href="/api/delete_checklist/{{ c.id }}" class="btn-action bg-light text-danger" onclick="return confirm('Delete?')">
                                    <i class="fa-solid fa-trash"></i>
                                </a>
                            </div>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
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
        <div class="alert alert-info small mb-3"><i class="fa-solid fa-mobile-screen"></i> This is how staff will see it.</div>
        <ul class="list-group" id="pList"></ul>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    function editList(data) {
        // Populate Form
        document.getElementById('list_id').value = data.id;
        document.getElementById('title').value = data.title;
        document.getElementById('frequency').value = data.frequency;
        document.getElementById('trigger_time').value = data.trigger_time || '';
        document.getElementById('tasks').value = JSON.stringify(JSON.parse(data.tasks)); // Unescape JSON
        
        // UI Changes
        document.getElementById('formTitle').innerText = "EDITING: " + data.title;
        document.getElementById('formTitle').className = "fw-bold text-primary m-0";
        document.getElementById('saveBtn').innerHTML = "<i class='fa-solid fa-check'></i> UPDATE";
        document.getElementById('resetBtn').style.display = 'block';
        
        // Scroll to form
        document.getElementById('checklistForm').scrollIntoView({behavior: 'smooth'});
    }

    function resetForm() {
        document.getElementById('checklistForm').reset();
        document.getElementById('list_id').value = '';
        document.getElementById('formTitle').innerText = "CREATE NEW CHECKLIST";
        document.getElementById('formTitle').className = "fw-bold text-muted m-0";
        document.getElementById('saveBtn').innerHTML = "<i class='fa-solid fa-save'></i> SAVE";
        document.getElementById('resetBtn').style.display = 'none';
    }

    function showPreview(title, tasksStr) {
        document.getElementById('pTitle').innerText = title;
        const list = document.getElementById('pList');
        list.innerHTML = '';
        
        const tasks = tasksStr.split(', '); // Simple split for preview
        tasks.forEach(t => {
            list.innerHTML += `<li class="list-group-item"><input class="form-check-input me-2" type="checkbox"> ${t}</li>`;
        });
        
        new bootstrap.Modal(document.getElementById('previewModal')).show();
    }
</script>
</body>
</html>"""

# --- 3. APPLY CHANGES ---
os.makedirs('templates', exist_ok=True)

with open('templates/login.html', 'w', encoding='utf-8') as f:
    f.write(login_html)
    print("✅ Created Premium Login Page")

with open('templates/settings.html', 'w', encoding='utf-8') as f:
    f.write(settings_html)
    print("✅ Created Advanced Settings Page")

print("\\n🚀 UI POLISH COMPLETE!")
print("1. Restart server: python3 app.py")
print("2. Check the new Login Page (Glass Effect)")
print("3. Check Settings -> Edit Checklists (Pencil Icon) -> Time Picker")