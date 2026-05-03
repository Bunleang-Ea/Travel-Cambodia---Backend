# Setup Guide - For Developers

Get the Travel Cambodia backend running in 5 minutes.

## Prerequisites

- Python 3.8+ installed
- Git installed
- Virtual environment (`.venv` folder)

## Setup Steps

### 1. Navigate to Project
```powershell
cd c:\Users\kakal\Downloads\back-end-security\Travel-Cambodia---Backend
```

### 2. Activate Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` at the start of your terminal line.

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run Migrations
```powershell
python manage.py migrate
```

### 5. Create Superuser (Admin Account)
```powershell
python manage.py createsuperuser
```

Follow the prompts:
- Email: `admin@example.com`
- Password: `YourSecurePassword123!`

### 6. Verify Setup
```powershell
python manage.py check
```

Should output: `System check identified no issues (0 silenced).`

### 7. Run Tests
```powershell
python manage.py test accounts --keepdb
```

Should output: `Ran 12 tests ... OK`

---

## Start Development

### Run Server
```powershell
python manage.py runserver
```

Visit: `http://localhost:8000/api/docs/`

### Access Admin Panel
1. Go to: `http://localhost:8000/admin/`
2. Login with superuser credentials

### Run Tests Anytime
```powershell
python manage.py test accounts --keepdb
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `.venv` folder missing | Create: `python -m venv .venv` |
| `pip` not found | Activate `.venv` first |
| Port 8000 in use | Use `python manage.py runserver 8001` |
| Can't migrate | Delete `db.sqlite3` and run migrate again |
| Tests fail | Check you're in correct directory |

---

## Project Structure

```
accounts/              👤 User authentication
├── models.py         User, OTP, Ticket models
├── views.py          API endpoints
├── serializers.py    Data validation
├── validators.py     Email/phone validation
├── admin.py          Django admin config
├── urls.py           Routes
└── tests.py          12 automated tests

core/                 ⚙️ Django configuration
├── settings.py       Security, CORS, throttling
├── urls.py           Main router
└── wsgi.py           Production config

itineraries/          🗺️ Trip planning
```

---

## Common Commands

```powershell
# Run server
python manage.py runserver

# Run all tests
python manage.py test accounts --keepdb

# Run specific test
python manage.py test accounts.AccountFlowTests.test_register_and_login --keepdb

# Create superuser
python manage.py createsuperuser

# Database reset (careful!)
rm db.sqlite3
python manage.py migrate

# Check system
python manage.py check

# Test coverage
pip install coverage
coverage run --source='accounts' manage.py test
coverage report
```

---

## What to Do Next

1. ✅ Complete this setup
2. Run tests to verify
3. Read [TESTING.md](TESTING.md)
4. Check [API_ENDPOINTS.md](API_ENDPOINTS.md)
5. Start developing!
