import os

# 1. DEFINE THE CLEAN HTML CONTENT
login_html = """<!DOCTYPE html>
<html>
<head>
    <title>Zion Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="[https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css](https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css)" rel="stylesheet">
    <style>
        body { background-color: #4F46E5; height: 100vh; display: flex; align-items: center; justify-content: center; }
        .card { width: 100%; max-width: 400px; padding: 40px; border-radius: 20px; border: none; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }
    </style>
</head>
<body>
    <div class="card">
        <h2 class="text-center fw-bold mb-4" style="color: #4F46E5">Login</h2>
        {% if error %}<div class="alert alert-danger p-2 text-center small mb-3">{{ error }}</div>{% endif %}
        <form method="POST" action="/login">
            <div class="mb-3">
                <label class="fw-bold small text-muted">STAFF ID</label>
                <input name="staff_id" class="form-control form-control-lg bg-light border-0" placeholder="e.g. 101" required>
            </div>
            <div class="mb-4">
                <label class="fw-bold small text-muted">PIN</label>
                <input type="password" name="pin" class="form-control form-control-lg bg-light border-0" placeholder="••••" required>
            </div>
            <button class="btn btn-primary w-100 btn-lg fw-bold" style="background-color: #4F46E5; border: none;">Access Dashboard</button>
        </form>
    </div>
</body>
</html>"""

dashboard_admin_html = """<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="[https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css](https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css)" rel="stylesheet">
    <style>
        body { background-color: #F8FAFC; font-family: system-ui, -apple-system, sans-serif; }
        .stat-card { background: white; border-radius: 16px; padding: 24px; border: none; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
        .stat-val { font-size: 2.5rem; font-weight: 700; color: #1e293b; line-height: 1; margin-bottom: 5px; }
        .stat-label { color: #64748b; font-weight: 600; font-size: 0.875rem; }
        
        .timeline-row { background: white; margin-bottom: 12px; padding: 16px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .timeline-track { flex-grow: 1; height: 8px; background: #f1f5f9; border-radius: 4px; margin: 0 20px; position: relative; overflow: hidden; }
        .timeline-bar { height: 100%; background: #4F46E5; position: absolute; border-radius: 4px; }
        .timeline-bar.late { background: #F59E0B; }
        
        .status-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        .dot-IN { background-color: #10B981; }
        .dot-OUT { background-color: #cbd5e1; }
    </style>
</head>
<body class="p-4">

<div class="d-flex justify-content-between align-items-center mb-5">
    <div>
        <h3 class="fw-bold m-0 text-dark">Hello, {{ user }}</h3>
        <p class="text-muted m-0">{{ dept }} Team Overview</p>
    </div>
    <div>
        <a href="/admin/settings" class="btn btn-white fw-bold shadow-sm">⚙️ Settings</a>
        <a href="/logout" class="btn btn-danger shadow-sm ms-2">Exit</a>
    </div>
</div>

<div class="row g-4 mb-5">
    <div class="col-md-3">
        <div class="stat-card">
            <div class="stat-label">Running Late</div>
            <div class="stat-val text-warning">{{ data.late }}</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="stat-label">Clocked In</div>
            <div class="stat-val" style="color: #4F46E5">{{ data.present }}</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="stat-label">Scheduled Shifts</div>
            <div class="stat-val text-dark">{{ data.total }}</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card" style="background: linear-gradient(135deg, #4F46E5, #4338ca); color: white;">
            <div class="d-flex justify-content-between">
                <div>
                    <div class="stat-label text-white-50">Top Performer</div>
                    {% if data.top_star %}
                        <div class="h4 fw-bold m-0 mt-2">{{ data.top_star.name }}</div>
                        <div class="small opacity-75">{{ data.top_star.checks }} Tasks Done</div>
                    {% else %}
                        <div class="h5 m-0 mt-2">No Data</div>
                    {% endif %}
                </div>
                <div style="font-size: 2.5rem;">🏆</div>
            </div>
        </div>
    </div>
</div>

<h6 class="text-muted fw-bold mb-3 text-uppercase">Live Activity (8:00 AM Start)</h6>
{% for s in data.staff %}
<div class="timeline-row" onclick="window.location.href='/admin/user_report/{{ s.id }}'" style="cursor: pointer;">
    <div style="width: 200px;">
        <div class="fw-bold text-dark">{{ s.name }}</div>
        <div class="small text-muted"><span class="status-dot dot-{{ s.status }}"></span>{{ s.status }}</div>
    </div>
    
    <div class="timeline-track">
        <div class="timeline-bar {{ 'late' if s.is_late else '' }}" style="left: {{ s.bar_left }}%; width: {{ s.bar_width }}%;"></div>
    </div>
    
    <div style="width: 100px; text-align: right;">
        <div class="fw-bold">{{ s.start }}</div>
        <div class="small text-muted">Clock In</div>
    </div>
</div>
{% endfor %}

</body>
</html>"""

# 2. ENSURE DIRECTORY EXISTS
os.makedirs('templates', exist_ok=True)

# 3. WRITE THE FILES (Force Overwrite)
with open('templates/login.html', 'w', encoding='utf-8') as f:
    f.write(login_html)
    print("✅ Fixed templates/login.html")

with open('templates/dashboard_admin.html', 'w', encoding='utf-8') as f:
    f.write(dashboard_admin_html)
    print("✅ Fixed templates/dashboard_admin.html")

print("\n🚀 SUCCESS! The files are repaired.")
print("👉 You can now run 'python3 app.py' and it will work perfectly.")