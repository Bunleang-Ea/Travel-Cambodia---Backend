# Testing Guide

Complete guide to test all features.

## Quick Test (1 minute)

```powershell
cd c:\Users\kakal\Downloads\back-end-security\Travel-Cambodia---Backend
python manage.py test accounts --keepdb
```

Expected: `Ran 12 tests ... OK` ✅

---

## What Gets Tested (12 Tests)

### Authentication Tests (4)
- User registration with validation
- User login and token generation
- Password reset via OTP
- Logout revokes token

### Security Tests (4)
- Admin endpoints protected (403 for non-admin)
- Authorization checks working
- Rate limiting configured
- CORS headers present

### Ticket Tests (2)
- Users can create tickets
- Only admins can respond

### System Tests (2)
- Health check working
- API docs available

---

## Manual Testing

### Option A: Use Test Scripts
```powershell
# Automated test suite
.\scripts\test_automated.ps1

# Manual feature tests
.\scripts\test_manual.ps1
```

### Option B: Use API Documentation
1. Start server: `python manage.py runserver`
2. Visit: `http://localhost:8000/api/docs/`
3. Try endpoints interactively

### Option C: Use PowerShell

Test registration:
```powershell
$body = @{
    email = "test@example.com"
    password = "TestPass123!"
    full_name = "Test User"
    phone_number = "+1-555-1234"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/accounts/register/" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body
```

---

## Test Coverage Report

```powershell
pip install coverage
coverage run --source='accounts' manage.py test
coverage report
coverage html
```

Then open `htmlcov/index.html` in browser.

**Target**: 80%+ coverage for accounts app

---

## Feature Testing Checklist

- [ ] Register new user
- [ ] Login with credentials
- [ ] Reset password via OTP
- [ ] View own profile
- [ ] Can't access admin endpoints (regular user)
- [ ] Bad email rejected
- [ ] Bad phone rejected
- [ ] Bad password rejected
- [ ] Create support ticket
- [ ] Admin can respond to ticket

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| Port already in use | Use `python manage.py runserver 8001` |
| Test database locked | Use `--keepdb` flag |
| Import errors | Activate `.venv`: `.\.venv\Scripts\Activate.ps1` |
| Can't find endpoints | Start server: `python manage.py runserver` |

---

## See Also

- [WINDOWS_TESTING.md](WINDOWS_TESTING.md) - Windows-specific help
- [API_ENDPOINTS.md](API_ENDPOINTS.md) - All API endpoints
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to add new tests
