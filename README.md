# Travel Cambodia Backend - Quick Start

Welcome! This is the backend for Travel Cambodia, a travel planning platform.

**Status: ✅ Ready for Frontend Integration**

---

## 📚 Documentation Roadmap

**Choose one based on your role:**

- 👤 **Developer** → Start with [docs/SETUP.md](docs/SETUP.md)
- 🧪 **QA/Tester** → Go to [docs/TESTING.md](docs/TESTING.md)
- 🪟 **Windows User** → Read [docs/WINDOWS_TESTING.md](docs/WINDOWS_TESTING.md)
- 📖 **Want Details** → See [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md)
- 💻 **Contributing** → Check [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
- 🔌 **API Reference** → Review [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md)

---

## ⚡ 2-Minute Quick Start

```powershell
# 1. Go to project directory
cd c:\Users\kakal\Downloads\back-end-security\Travel-Cambodia---Backend

# 2. Activate environment
.\.venv\Scripts\Activate.ps1

# 3. Run tests (verify everything works)
python manage.py test accounts --keepdb

# Expected: "Ran 12 tests ... OK"

# 4. Start development server
python manage.py runserver

# 5. Visit http://localhost:8000/api/docs/ for interactive API docs
```

---

## 📁 Project Structure

```
Travel-Cambodia---Backend/
├── docs/                      📚 All documentation (start here!)
├── scripts/                   🔧 Testing & utility scripts
├── accounts/                  👤 Authentication & users
├── core/                      ⚙️ Django settings
├── itineraries/               🗺️ Trip planning
├── manage.py                  🚀 Run this with "python manage.py ..."
└── requirements.txt           📦 Python packages
```

---

## ✅ What's Built

| Feature | Status |
|---------|--------|
| User Registration | ✅ Done |
| Login/Logout | ✅ Done |
| Password Reset (OTP) | ✅ Done |
| Admin Management | ✅ Done |
| Support Tickets | ✅ Done |
| Input Validation | ✅ Done |
| Security (CORS, etc) | ✅ Done |
| API Documentation | ✅ Done |
| Tests | ✅ 12/12 Passing |

---

## 🎯 Next Steps

1. **Learn the setup** → [docs/SETUP.md](docs/SETUP.md)
2. **Run tests** → `python manage.py test accounts --keepdb`
3. **Test features** → Use [docs/TESTING.md](docs/TESTING.md) or `/api/docs/`
4. **Read code** → Check `accounts/` folder
5. **Make changes** → Follow [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

---

## 🆘 Need Help?

| Problem | Solution |
|---------|----------|
| Can't find manage.py | Check you're in: `Travel-Cambodia---Backend/` |
| Tests won't run | Read [docs/WINDOWS_TESTING.md](docs/WINDOWS_TESTING.md) |
| Port 8000 in use | Use `python manage.py runserver 8001` |
| Question about API | See [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md) |
---

**Ready to start?** → Open [docs/SETUP.md](docs/SETUP.md)
