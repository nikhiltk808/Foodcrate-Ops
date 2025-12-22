# Staff Dashboard Bug Fixes and Admin Link

## Summary of Changes

This PR fixes critical bugs in the staff dashboard and adds a navigation link to the admin dashboard for authorized users.

## Bugs Fixed

### 1. Missing Template Variables (routes_staff.py)
**Issue**: The `user_id` and `user_role` session variables were not being passed to the template, causing undefined variable errors in the template.

**Fix**: Updated the `render_template` call to pass these variables:
```python
# Before
return render_template('dashboard_staff.html', theme=h.THEME, user=session['user_name'],
                       current_status=current_status, tasks=task_groups, stats=stats,
                       kpi=kpi, current_date=today_str,
                       updates=updates, duties=duties, snapshot=snapshot,
                       todos=todos, logs=logs)

# After
return render_template('dashboard_staff.html', theme=h.THEME, user=session['user_name'],
                       user_id=session['user_id'], user_role=session.get('user_role'),
                       current_status=current_status, tasks=task_groups, stats=stats,
                       kpi=kpi, current_date=today_str,
                       updates=updates, duties=duties, snapshot=snapshot,
                       todos=todos, logs=logs)
```

### 2. Invalid Session Access in Template (dashboard_staff.html)
**Issue**: The template was trying to access `{{ session.user_id }}` directly, which doesn't work in Jinja2 templates without explicit configuration.

**Fix**: Updated to use the passed variable:
```html
<!-- Before -->
<div class="container" data-user-id="{{ session.user_id }}">

<!-- After -->
<div class="container" data-user-id="{{ user_id }}">
```

## Feature Added

### Admin Dashboard Link for Managers
Added a navigation link in the staff dashboard header that allows users with the 'manager' role to quickly access the admin dashboard.

**Implementation**:
```html
<div style="display: flex; align-items: center; gap: 10px;">
    {% if user_role == 'manager' %}
    <a href="/" style="text-decoration: none; background: var(--primary-light); color: var(--primary); padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 5px;">
        <span class="material-icons" style="font-size:18px;">admin_panel_settings</span>
        <span>Admin</span>
    </a>
    {% endif %}
    <div class="user-pill">
        <span>{{ user }}</span>
        <a href="/logout">
            <span class="material-icons" style="font-size:18px; color:var(--primary);">logout</span>
        </a>
    </div>
</div>
```

**Key Features**:
- Only visible when `user_role == 'manager'`
- Styled consistently with existing UI using Material Icons
- Positioned next to the logout button in the header
- Uses the app's primary color scheme for consistency

## Visual Changes

### Before:
```
[Logo]                                              [User Name] [Logout]
```

### After (for manager users):
```
[Logo]                                    [Admin Icon + Text] [User Name] [Logout]
```

### After (for regular staff):
```
[Logo]                                              [User Name] [Logout]
```
(No admin link visible for non-manager users)

## Testing

All changes have been tested with the included test script (`test_fixes.py`):

```bash
$ python3 test_fixes.py
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

## Files Changed

1. **routes_staff.py**: Added `user_id` and `user_role` to template context
2. **templates/dashboard_staff.html**: 
   - Fixed `data-user-id` to use passed variable
   - Added conditional admin dashboard link

## Security Considerations

- The admin link is rendered conditionally based on `user_role`, which is set server-side from the session
- Even if a malicious user modifies the HTML to add the link, they cannot access admin routes without proper authentication
- The admin routes themselves have role-based access controls (checking `session.get('user_role')`)

## Backwards Compatibility

These changes are fully backwards compatible:
- No changes to database schema
- No changes to API endpoints
- No breaking changes to existing functionality
- Only additive changes to the UI

## Future Enhancements

Possible future improvements:
- Add breadcrumb navigation
- Add more role-based menu items
- Implement a full navigation menu system
