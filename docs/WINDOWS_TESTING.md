# Windows Testing Guide

Testing on Windows PowerShell with special tips.

## Quick Start

```powershell
cd c:\Users\kakal\Downloads\back-end-security\Travel-Cambodia---Backend
python manage.py test accounts --keepdb
```

Done! If you see `OK` ✅ everything works.

---

## Testing Methods on Windows

### Method 1: Automated Tests (RECOMMENDED)

```powershell
python manage.py test accounts --keepdb
```

Pros: Fast, reliable, tests everything
Time: ~1 minute

### Method 2: PowerShell Script

```powershell
.\scripts\test_manual.ps1
```

Pros: See each feature tested
Time: ~2 minutes

### Method 3: Interactive API Docs

1. Start server: `python manage.py runserver`
2. Visit: `http://localhost:8000/api/docs/`
3. Click on endpoints to test interactively

Pros: Visual, easy
Time: As long as you want

### Method 4: curl.exe (Windows 10+)

```powershell
curl.exe -X POST http://localhost:8000/api/accounts/register/ `
    -H "Content-Type: application/json" `
    -d '{"email":"test@example.com","password":"TestPass123!"}'
```

**Note**: Use `curl.exe` NOT `curl` (curl is PowerShell alias)

---

## Common Windows Issues

### Issue: "python not found"
```powershell
# Make sure virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Check Python version
python --version
```

### Issue: "Can't find manage.py"
```powershell
# You're in the wrong directory
cd c:\Users\kakal\Downloads\back-end-security\Travel-Cambodia---Backend
```

### Issue: "curl: command not found"
```powershell
# Use Windows curl.exe instead
curl.exe -X POST ...

# OR use PowerShell's Invoke-WebRequest
$body = @{...} | ConvertTo-Json
Invoke-WebRequest -Uri "http://..." -Method POST -Body $body
```

### Issue: Port 8000 already in use
```powershell
# Use a different port
python manage.py runserver 8001

# Then visit http://localhost:8001/api/docs/
```

---

## Testing Checklist for Windows Users

- [ ] Activate virtual environment
- [ ] Run `python manage.py test accounts --keepdb`
- [ ] See "OK" in output
- [ ] Start server: `python manage.py runserver`
- [ ] Visit `http://localhost:8000/api/docs/`
- [ ] Test a few endpoints interactively
- [ ] Everything works! ✅

---

## PowerShell Testing Script

Create file `test.ps1`:

```powershell
$API = "http://localhost:8000/api"

# Test 1: Health
Write-Host "Testing health..." -ForegroundColor Cyan
$response = Invoke-WebRequest -Uri "$API/health/" -Method GET
Write-Host "✓ Health: OK" -ForegroundColor Green

# Test 2: Register
Write-Host "Testing registration..." -ForegroundColor Cyan
$body = @{
    email = "test$(Get-Random)@example.com"
    password = "TestPass123!"
    full_name = "Test User"
    phone_number = "+1-555-1234"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "$API/accounts/register/" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body

Write-Host "✓ Registration: OK" -ForegroundColor Green

# Test 3: Protected endpoint
Write-Host "Testing auth requirement..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$API/accounts/me/" -ErrorAction Stop
    Write-Host "✗ Should require auth!" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "✓ Auth required: OK" -ForegroundColor Green
    }
}

Write-Host "`n✅ All tests passed!" -ForegroundColor Green
```

Run with: `.\test.ps1`

---

## Quick Links

- 📖 [SETUP.md](SETUP.md) - How to set up
- 🧪 [TESTING.md](TESTING.md) - Detailed testing guide
- 🔌 [API_ENDPOINTS.md](API_ENDPOINTS.md) - All endpoints
