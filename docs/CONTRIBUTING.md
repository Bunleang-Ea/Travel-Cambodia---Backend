# Contributing Guide

How to make changes to this project safely.

## Before You Code

1. Run tests: `python manage.py test accounts --keepdb`
2. Make sure you get `OK` ✅
3. Create a new branch if using Git
4. Read the [API_ENDPOINTS.md](API_ENDPOINTS.md) to understand existing structure

---

## Adding Features

### 1. Create Your Feature
```python
# In accounts/models.py (if adding a model)
class YourModel(models.Model):
    # Your fields
    pass

# In accounts/views.py (if adding an endpoint)
class YourView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Your code
        return Response(data)
```

### 2. Add Validation
```python
# In accounts/serializers.py or validators.py
def validate_your_field(value):
    if not valid:
        raise ValidationError("Error message")
    return value
```

### 3. Create Tests
```python
# In accounts/tests.py
def test_your_feature(self):
    response = self.client.post(url, data)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.data['field'], expected_value)
```

### 4. Update Routes
```python
# In accounts/urls.py
path('your-endpoint/', YourView.as_view(), name='your-endpoint')
```

### 5. Run Tests
```powershell
python manage.py test accounts --keepdb -v 2
```

Make sure all tests pass! ✅

---

## Code Style

### Naming Conventions
- **Classes**: `PascalCase` (UserView, PasswordResetOTP)
- **Functions**: `snake_case` (get_user, validate_email)
- **Constants**: `UPPER_CASE` (DEFAULT_TIMEOUT, MAX_SIZE)
- **URL names**: `kebab-case` (account-register, password-reset-request)

### Best Practices
- Use Django ORM (no raw SQL)
- Add docstrings to functions
- Keep functions small (< 20 lines)
- Use type hints where possible
- Handle errors with try/except
- Add input validation

### Example
```python
def validate_email_format(email: str) -> str:
    """
    Validate email format using RFC 5322 standard.
    
    Args:
        email: Email address to validate
        
    Returns:
        Normalized email (lowercase)
        
    Raises:
        ValidationError: If email is invalid
    """
    if not isinstance(email, str):
        raise ValidationError("Email must be a string")
    
    # ... validation logic
    return email.lower()
```

---

## Adding Tests

### Test Structure
```python
class YourTestCase(APITestCase):
    def setUp(self):
        # Create test data
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
        self.token = Token.objects.create(user=self.user)
    
    def test_your_feature(self):
        # Test your feature
        response = self.client.get(
            '/api/endpoint/',
            HTTP_AUTHORIZATION=f'Token {self.token.key}'
        )
        self.assertEqual(response.status_code, 200)
```

### Test Guidelines
- One test per feature/scenario
- Use descriptive names: `test_admin_cannot_delete_self`
- Test both success and failure cases
- Mock external services (email, etc)
- Aim for 80%+ coverage

---

## Commit Guidelines

### Good Commit Messages
```
git commit -m "Add email validation for registration"
git commit -m "Fix: Admin couldn't delete users"
git commit -m "Test: Add coverage for password reset"
```

### Bad Commit Messages
```
git commit -m "Fixed stuff"
git commit -m "Update"
git commit -m "Oops"
```

---

## Before Submitting

Run this checklist:

- [ ] Code follows style guide
- [ ] All tests pass: `python manage.py test accounts --keepdb`
- [ ] No TODO/FIXME comments left
- [ ] Docstrings added to new functions
- [ ] Input validation added
- [ ] Error handling included
- [ ] Documentation updated if needed
- [ ] No hardcoded values (use settings.py)

---

## File Locations

| What | Where |
|------|-------|
| Models | accounts/models.py |
| Views | accounts/views.py |
| Serializers | accounts/serializers.py |
| Validators | accounts/validators.py |
| Tests | accounts/tests.py |
| Routes | accounts/urls.py |
| Admin | accounts/admin.py |
| Settings | core/settings.py |
| Tests | Do NOT create new test files |
| Docs | docs/ folder |

---

## Common Changes

### Add New Endpoint
1. Create view in `accounts/views.py`
2. Create serializer in `accounts/serializers.py`
3. Add route to `accounts/urls.py`
4. Add tests in `accounts/tests.py`
5. Run: `python manage.py test accounts --keepdb`

### Change User Model
1. Edit `accounts/models.py`
2. Create migration: `python manage.py makemigrations`
3. Run migration: `python manage.py migrate`
4. Update serializer if needed
5. Run tests

### Add Validation
1. Add to `accounts/validators.py` OR `accounts/serializers.py`
2. Add test case
3. Run: `python manage.py test accounts --keepdb`

---

## Security Rules

Always follow these:

- ✅ Use Django ORM (no raw SQL)
- ✅ Validate all inputs
- ✅ Use permission_classes on views
- ✅ Hash passwords (Django does this)
- ✅ Check authorization in views
- ✅ Don't log sensitive data
- ✅ Use HTTPS in production
- ✅ Sanitize error messages

Never do this:
- ❌ Raw SQL queries
- ❌ Unvalidated user input
- ❌ Hardcoded passwords/secrets
- ❌ Plaintext password logs
- ❌ No permission checks
- ❌ Trust user_id from frontend

---

## Getting Help

- Check existing code in accounts/
- Read Django docs: https://docs.djangoproject.com/
- Review tests for examples
- Check IMPLEMENTATION_STATUS.md
- Ask in comments

---

## Summary

1. **Read** the existing code
2. **Code** following the style guide
3. **Test** your changes
4. **Document** what you did
5. **Submit** only when tests pass ✅
