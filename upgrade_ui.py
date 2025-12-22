import os

# --- 1. MODERN ADMIN DASHBOARD (Professional UI) ---
admin_dashboard_html = """<!DOCTYPE html>
<html>
<head>
    <title>Zion Command Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        :root {
            --primary: #4361ee;
            --primary-dark: #3a0ca3;
            --secondary: #aeb8c3;
            --success: #06d6a0;
            --warning: #ffd166;
            --danger: #ef476f;
            --bg: #f8f9fa;
            --glass: rgba(255, 255, 255, 0.95);
        }
        
        body { background-color: var(--bg); font-family: 'Inter', sans-serif; color: #2b2d42; }
        
        /* Navbar */
        .navbar { background: white; box-shadow: 0 2px 15px rgba(0,0,0,0.04); padding: 15px 0; }
        .nav-btn { font-weight: 600; border-radius: 8px; transition: 0.2s; }
        
        /* Stats Cards */
        .stat-card {
            background: white; border: none; border-radius: 16px;
            padding: 25px; height: 100%; position: relative; overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.03); transition: transform 0.2s;
        }
        .stat-card:hover { transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.08); }
        
        .stat-icon-bg {
            position: absolute; right: -10px; top: -10px;
            font-size: 5rem; opacity: 0.05; transform: rotate(15deg);
        }
        
        .stat-value { font-size: 2.8rem; font-weight: 800; line-height: 1; margin-bottom: 5px; color: #2b2d42; }
        .stat-label { font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #8d99ae; }
        
        /* Star Performer Card (Gradient) */
        .card-gradient {
            background: linear-gradient(135deg, #4361ee 0%, #3a0ca3 100%);
            color: white;
        }
        .card-gradient .stat-value, .card-gradient .stat-label { color: white; }
        .card-gradient .stat-label { opacity: 0.8; }
        .card-gradient .stat-icon-bg { opacity: 0.2; color: white; }

        /* Timeline */
        .section-title { font-size: 0.8rem; font-weight: 800; color: #8d99ae; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }
        
        .timeline-row {
            background: white; margin-bottom: 12px; padding: 15px 20px;
            border-radius: 12px; display: flex; align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02); border-left: 5px solid transparent;
            cursor: pointer; transition: 0.2s;
        }
        .timeline-row:hover { transform: scale(1.01); box-shadow: 0 5px 15px rgba(0,0,0,0.05); }
        
        .status-IN { border-left-color: var(--success); }
        .status-OUT { border-left-color: var(--secondary); opacity: 0.8; }
        .status-BREAK { border-left-color: var(--warning); }
        
        .timeline-track {
            flex-grow: 1; height: 10px; background: #e9ecef;
            border-radius: 5px; margin: 0 25px; position: relative; overflow: hidden;
        }
        .timeline-bar { height: 100%; background: var(--primary); position: absolute; border-radius: 5px; box-shadow: 0 2px 5px rgba(67, 97, 238, 0.4); }
        .timeline-bar.late { background: var(--warning); }
        
        .avatar-circle {
            width: 40px; height: 40px; background: #edf2fb; color: var(--primary);
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font-weight: 700; margin-right: 15px;
        }
    </style>
</head>
<body class="pb-5">

<nav class="navbar mb-5">
    <div class="container">
        <div class="d-flex align-items-center">
            <span class="fs-4 me-2">🏔️</span>
            <div>
                <h5 class="fw-bold m-0 text-dark">Zion Ops</h5>
                <small class="text-muted fw-bold" style="font-size: 0.75rem;">{{ dept }} MANAGER VIEW</small>
            </div>
        </div>
        <div class="d-flex gap-2">
            <a href="/admin/settings" class="btn btn-light nav-btn border"><i class="fa-solid fa-sliders"></i> Settings</a>
            <a href="/logout" class="btn btn-danger nav-btn"><i class="fa-solid fa-power-off"></i></a>
        </div>
    </div>
</nav>

<div class="container">
    <div class="row g-4 mb-5">
        <div class="col-md-3">
            <div class="stat-card">
                <i class="fa-solid fa-user-clock stat-icon-bg"></i>
                <div class="stat-label">On Duty</div>
                <div class="stat-value text-success">{{ data.present }}</div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="stat-card">
                <i class="fa-solid fa-triangle-exclamation stat-icon-bg text-warning"></i>
                <div class="stat-label">Late Arrivals</div>
                <div class="stat-value text-warning">{{ data.late }}</div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="stat-card">
                <i class="fa-solid fa-users stat-icon-bg"></i>
                <div class="stat-label">Team Size</div>
                <div class="stat-value">{{ data.total }}</div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="stat-card card-gradient">
                <i class="fa-solid fa-trophy stat-icon-bg"></i>
                <div class="d-flex flex-column h-100 justify-content-center">
                    <div class="stat-label text-white-50">⭐ Top Performer</div>
                    {% if data.top_star %}
                        <div class="h3 fw-bold m-0 mt-2">{{ data.top_star.name }}</div>
                        <div class="small opacity-75 mt-1"><i class="fa-solid fa-check-double"></i> {{ data.top_star.checks }} Tasks Done</div>
                    {% else %}
                        <div class="h4 m-0 mt-2">No Data Yet</div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>

    <div class="card border-0 shadow-sm rounded-4 mb-5" style="background: #fff;">
        <div class="card-body p-4">
            <form action="/api/quick_assign" method="POST" class="row g-3 align-items-center">
                <div class="col-auto">
                    <div class="avatar-circle bg-warning text-white"><i class="fa-solid fa-bolt"></i></div>
                </div>
                <div class="col">
                    <input type="text" name="task_title" class="form-control form-control-lg border-0 bg-light" placeholder="⚡ Quick Task (e.g. 'VIP in Table 5', 'Clean Freezer')" required>
                </div>
                <div class="col-md-3">
                    <select name="assign_to" class="form-select form-select-lg border-0 bg-light">
                        <option value="all">Assign to Everyone</option>
                        {% for s in data.staff %}
                            <option value="{{ s.id }}">{{ s.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-auto">
                    <button type="submit" class="btn btn-primary btn-lg px-4 rounded-3"><i class="fa-solid fa-paper-plane"></i></button>
                </div>
            </form>
        </div>
    </div>

    <div class="d-flex justify-content-between align-items-end mb-3">
        <div class="section-title m-0"><i class="fa-regular fa-clock me-2"></i> Live Shift Timeline (8:00 AM Start)</div>
        <div class="small text-muted"><span class="badge bg-success rounded-pill me-1">&nbsp;</span>Active <span class="badge bg-secondary rounded-pill ms-2 me-1">&nbsp;</span>Off</div>
    </div>

    {% for s in data.staff %}
    <div class="timeline-row status-{{ s.status }}" onclick="window.location.href='/admin/user_report/{{ s.id }}'">
        <div class="d-flex align-items-center" style="width: 220px;">
            <div class="avatar-circle">
                {{ s.name[:1] }}
            </div>
            <div>
                <div class="fw-bold text-dark">{{ s.name }}</div>
                <div class="small text-muted" style="font-size: 0.75rem;">{{ s.dept }}</div>
            </div>
        </div>
        
        <div class="timeline-track">
            {% if s.status != 'OUT' %}
                <div class="timeline-bar {{ 'late' if s.is_late else '' }}" 
                     style="left: {{ s.bar_left }}%; width: {{ s.bar_width }}%;"
                     title="Started: {{ s.start }}"></div>
            {% endif %}
        </div>
        
        <div style="width: 120px; text-align: right;">
            {% if s.status != 'OUT' %}
                <div class="fw-bold text-dark">{{ s.start }}</div>
                <div class="small text-muted"><i class="fa-solid fa-stopwatch"></i> Clock In</div>
            {% else %}
                <div class="badge bg-light text-secondary">OFF DUTY</div>
            {% endif %}
        </div>
    </div>
    {% endfor %}

</div>
</body>
</html>"""

# --- 2. SETTINGS PAGE (With All Checklist Types) ---
settings_html = """<!DOCTYPE html>
<html>
<head>
    <title>Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background: #f8f9fa; font-family: 'Segoe UI', sans-serif; }
        .navbar { background: #4361ee; }
        .card { border: none; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
        .form-label { font-weight: 600; font-size: 0.8rem; color: #6c757d; text-transform: uppercase; }
        .btn-primary { background: #4361ee; border: none; }
        .list-group-item { border: none; border-bottom: 1px solid #eee; }
    </style>
</head>
<body class="pb-5">

<nav class="navbar navbar-dark mb-4 p-3">
    <div class="container">
        <a href="/" class="btn btn-outline-light btn-sm fw-bold"><i class="fa-solid fa-arrow-left"></i> Dashboard</a>
        <span class="navbar-brand fw-bold">⚙️ System Configuration</span>
    </div>
</nav>

<div class="container">
    <div class="row g-4">
        
        <div class="col-md-12">
            <div class="card p-4">
                <h5 class="fw-bold mb-3 text-primary"><i class="fa-solid fa-user-plus"></i> Add New Staff</h5>
                <form action="/api/add_user" method="POST" class="row g-3">
                    <div class="col-md-2">
                        <label class="form-label">Staff ID</label>
                        <input name="staff_id" class="form-control" placeholder="101" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">PIN</label>
                        <input name="pin" class="form-control" placeholder="****" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Full Name</label>
                        <input name="name" class="form-control" placeholder="John Doe" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Department</label>
                        <select name="department" class="form-select">
                            <option value="Service">Service</option>
                            <option value="Kitchen">Kitchen</option>
                            <option value="Admin">Admin</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Role</label>
                        <select name="role" class="form-select">
                            <option value="staff">Staff</option>
                            <option value="manager">Manager</option>
                        </select>
                    </div>
                    <div class="col-md-1 d-flex align-items-end">
                        <button class="btn btn-success w-100"><i class="fa-solid fa-plus"></i></button>
                    </div>
                </form>
                
                <div class="mt-4 p-3 bg-light rounded">
                    <h6 class="text-muted fw-bold small mb-3">EXISTING STAFF</h6>
                    <div class="row g-2">
                        {% for u in users %}
                        <div class="col-md-3">
                            <div class="bg-white p-2 rounded border d-flex justify-content-between align-items-center">
                                <small><strong>{{ u.staff_id }}</strong> {{ u.name }}</small>
                                {% if u.staff_id != '999' %}
                                <a href="/api/delete_user/{{ u.id }}" class="text-danger small"><i class="fa-solid fa-trash"></i></a>
                                {% endif %}
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>

        <div class="col-md-12">
            <div class="card p-4 border-start border-5 border-primary">
                <h5 class="fw-bold mb-3 text-primary"><i class="fa-solid fa-list-check"></i> Checklist Creator</h5>
                <form action="/api/add_checklist" method="POST">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">Checklist Title</label>
                            <input name="title" class="form-control" placeholder="e.g. Opening Procedures" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Frequency / Type</label>
                            <select name="frequency" class="form-select">
                                <option value="Daily">Daily Routine</option>
                                <option value="Weekly">Weekly Deep Clean</option>
                                <option value="Monthly">Monthly Inventory</option>
                                <option value="Event">Event Specific</option>
                            </select>
                        </div>
                        <div class="col-12">
                            <label class="form-label">Tasks (JSON Format)</label>
                            <textarea name="tasks" class="form-control" rows="3" placeholder='["Turn on lights", "Check temperature", "Wipe counters"]' style="font-family: monospace;" required></textarea>
                            <div class="form-text">Enter tasks as a list inside brackets: ["Task 1", "Task 2"]</div>
                        </div>
                        <div class="col-12 text-end">
                            <button class="btn btn-primary px-4 fw-bold">Create Checklist</button>
                        </div>
                    </div>
                </form>
                
                <hr class="my-4">
                <h6 class="text-muted fw-bold small">ACTIVE CHECKLISTS</h6>
                <ul class="list-group">
                    {% for c in checklists %}
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        <div>
                            <strong>{{ c.title }}</strong> 
                            <span class="badge bg-secondary ms-2">{{ c.frequency }}</span>
                        </div>
                        <small class="text-muted">{{ c.tasks_str }}</small>
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </div>

    </div>
</div>
</body>
</html>"""

# 2. WRITE THE FILES
os.makedirs('templates', exist_ok=True)

with open('templates/dashboard_admin.html', 'w', encoding='utf-8') as f:
    f.write(admin_dashboard_html)
    print("✅ Created Modern Dashboard (templates/dashboard_admin.html)")

with open('templates/settings.html', 'w', encoding='utf-8') as f:
    f.write(settings_html)
    print("✅ Created Enhanced Settings (templates/settings.html)")

print("\\n🚀 UI UPGRADE COMPLETE!")
print("1. Restart your server: python3 app.py")
print("2. Login (999 / admin)")
print("3. You will see the new Glassmorphism UI.")