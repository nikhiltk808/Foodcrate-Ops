# Testing and Verification Guide

## How to Test the Changes

### Prerequisites
1. Ensure Flask and dependencies are installed:
   ```bash
   pip3 install flask werkzeug
   ```

2. Initialize the database:
   ```bash
   python3 -c "import database as db; db.init_db()"
   ```

### Running the Automated Tests
```bash
python3 test_fixes.py
```

Expected output:
```
============================================================
Running Staff Dashboard Bug Fix Tests
============================================================
Testing database setup...
✅ Database has 1 manager user(s)

Testing route imports...
✅ All route modules imported successfully

Testing Flask app configuration...
✅ All required blueprints registered: ['staff', 'api', 'admin']

Testing staff dashboard route...
✅ Staff dashboard renders correctly for manager user
   - Contains data-user-id attribute
   - Contains admin link for manager role

Testing staff user (non-manager) view...
✅ Staff dashboard renders correctly for regular staff user
   - Admin link conditional rendering is in place

============================================================
Test Summary
============================================================
Passed: 5/5

✅ All tests passed!
```

### Manual Testing

#### 1. Start the Flask Server
```bash
python3 app.py
```

The server will start on `http://127.0.0.1:5001`

#### 2. Test Manager User Flow
1. Navigate to `http://127.0.0.1:5001/login`
2. Login with:
   - Name: `Admin`
   - PIN: `1234`
3. You should be redirected to the admin dashboard
4. Navigate to the staff view: `http://127.0.0.1:5001/staff/1`
5. **Verify**: You should see an "Admin" link in the header next to the logout button
6. Click the "Admin" link
7. **Verify**: You should be redirected to the admin dashboard

#### 3. Test Regular Staff User Flow
1. First, create a test staff user (if not exists):
   ```python
   python3 -c "
   import database as db
   with db.get_db() as conn:
       conn.execute('INSERT INTO users (name, pin, role, department) VALUES (?, ?, ?, ?)',
                    ('TestStaff', '0000', 'staff', 'Kitchen'))
       conn.commit()
   "
   ```

2. Logout and login as TestStaff:
   - Name: `TestStaff`
   - PIN: `0000`
3. Navigate to the staff dashboard
4. **Verify**: The "Admin" link should NOT be visible in the header
5. **Verify**: Only the user name and logout button are visible

### Visual Verification Checklist

#### For Manager Users:
- [ ] Logo displayed correctly on the left
- [ ] "Admin" link visible with admin icon
- [ ] "Admin" link styled with primary color (blue)
- [ ] User name pill displayed
- [ ] Logout icon displayed
- [ ] All elements properly aligned in header

#### For Staff Users:
- [ ] Logo displayed correctly on the left
- [ ] NO "Admin" link visible
- [ ] User name pill displayed
- [ ] Logout icon displayed
- [ ] Header looks clean without the admin link

### Browser Testing
Test in multiple browsers to ensure compatibility:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Mobile browsers (responsive design)

### Edge Cases to Test
1. **Session expiry**: Ensure users are redirected to login when session expires
2. **Role changes**: If a user's role changes, ensure the UI reflects the change on next login
3. **Multiple tabs**: Verify logout in one tab invalidates session in all tabs
4. **Direct URL access**: Try accessing admin routes directly as a staff user

## Security Tests

### 1. Template Injection
- [ ] Verify user input is properly escaped in templates
- [ ] No raw HTML rendering from user data

### 2. Session Security
- [ ] Session cookies are HttpOnly
- [ ] Session data cannot be manipulated client-side
- [ ] Role checks are performed server-side

### 3. Authorization
- [ ] Admin routes reject non-manager users
- [ ] Staff can only access their own dashboard
- [ ] Managers can access any staff dashboard

## Performance Tests

### 1. Page Load Time
Measure the staff dashboard load time:
```bash
curl -w "@curl-format.txt" -o /dev/null -s http://127.0.0.1:5001/staff/1
```

### 2. Database Query Efficiency
Check that the added variables don't cause additional database queries:
- Original queries: Count before changes
- New queries: Count after changes
- **Expected**: No increase in query count

## Cleanup After Testing

Remove test user:
```bash
python3 -c "
import database as db
with db.get_db() as conn:
    conn.execute('DELETE FROM users WHERE name=?', ('TestStaff',))
    conn.commit()
"
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'flask'"
**Solution**: Install Flask: `pip3 install flask werkzeug`

### Issue: "sqlite3.OperationalError: no such table: users"
**Solution**: Initialize database: `python3 -c "import database as db; db.init_db()"`

### Issue: "Admin link not showing for manager"
**Checklist**:
1. Verify user has role='manager' in database
2. Check that user_role is passed to template in routes_staff.py
3. Verify session contains user_role
4. Check template syntax: `{% if user_role == 'manager' %}`

### Issue: "data-user-id shows as empty"
**Checklist**:
1. Verify user_id is passed to template in routes_staff.py
2. Check session contains user_id
3. Verify template uses `{{ user_id }}` not `{{ session.user_id }}`
