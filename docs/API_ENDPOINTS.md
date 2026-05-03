# API Endpoints Reference

Complete list of all API endpoints in Travel Cambodia backend.

## Authentication Endpoints

### Register User
```
POST /api/accounts/register/
```
**Body:**
```json
{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "phone_number": "+1-555-1234"
}
```
**Response:** User details + auth token

### Login
```
POST /api/accounts/login/
```
**Body:**
```json
{
    "email": "user@example.com",
    "password": "SecurePass123!"
}
```
**Response:** User details + auth token

### Get Profile
```
GET /api/accounts/me/
Authorization: Token <your_token>
```

### Update Profile
```
PUT /api/accounts/me/
Authorization: Token <your_token>

Body (any or all fields):
{
    "full_name": "New Name",
    "phone_number": "+1-555-5678",
    "profile_picture_url": "https://...",
    "profile_picture": <file>
}
```

### Logout
```
POST /api/accounts/logout/
Authorization: Token <your_token>
```

---

## Password Reset

### Request Reset (OTP)
```
POST /api/accounts/password-reset/request/

Body:
{
    "email": "user@example.com"
}
```
OTP sent to email (console in development)

### Confirm Reset
```
POST /api/accounts/password-reset/confirm/

Body:
{
    "email": "user@example.com",
    "otp": "123456",
    "new_password": "NewPass123!"
}
```

---

## Support Tickets

### List Tickets
```
GET /api/accounts/support-tickets/
Authorization: Token <your_token>
```
Returns: Own tickets (users) or all tickets (admins)

### Create Ticket
```
POST /api/accounts/support-tickets/
Authorization: Token <your_token>

Body:
{
    "subject": "Cannot login",
    "description": "I forgot my password..."
}
```

### Get Ticket Details
```
GET /api/accounts/support-tickets/<id>/
Authorization: Token <your_token>
```

### Admin Respond to Ticket
```
POST /api/accounts/support-tickets/<id>/respond/
Authorization: Token <admin_token>

Body:
{
    "status": "in_progress",
    "response": "We are checking your issue..."
}
```

---

## Admin Endpoints

### List Users
```
GET /api/accounts/admin/users/
Authorization: Token <admin_token>
```

### Create User
```
POST /api/accounts/admin/users/create/
Authorization: Token <admin_token>

Body:
{
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "full_name": "New User",
    "phone_number": "+1-555-1234",
    "is_staff": false
}
```

### Delete User
```
DELETE /api/accounts/admin/users/<id>/delete/
Authorization: Token <admin_token>
```

---

## Role Management

### List Roles
```
GET /api/accounts/admin/roles/
Authorization: Token <admin_token>
```

### Assign Role
```
POST /api/accounts/admin/roles/assign/
Authorization: Token <admin_token>

Body:
{
    "email": "user@example.com",
    "role": "support"
}
```

### Remove Role
```
POST /api/accounts/admin/roles/remove/
Authorization: Token <admin_token>

Body:
{
    "email": "user@example.com",
    "role": "support"
}
```

---

## Permissions

### List Permissions
```
GET /api/accounts/admin/permissions/
Authorization: Token <admin_token>
```

### Assign Permission to Role
```
POST /api/accounts/admin/roles/permissions/assign/
Authorization: Token <admin_token>

Body:
{
    "group": "support",
    "permission": "<permission_id>"
}
```

### Remove Permission from Role
```
POST /api/accounts/admin/roles/permissions/remove/
Authorization: Token <admin_token>

Body:
{
    "group": "support",
    "permission": "<permission_id>"
}
```

---

## System Endpoints

### Health Check
```
GET /api/health/
```
**Response:**
```json
{"status": "ok"}
```

### API Schema
```
GET /api/schema/
```
Returns OpenAPI/Swagger schema

### API Documentation
```
GET /api/docs/
```
Interactive Swagger UI

---

## Itinerary Endpoints

### List Itineraries
```
GET /api/itineraries/
Authorization: Token <your_token>
```

### Create Itinerary
```
POST /api/itineraries/
Authorization: Token <your_token>

Body:
{
    "title": "Cambodia Trip",
    "description": "3-day trip",
    "start_date": "2024-01-01",
    "end_date": "2024-01-03"
}
```

### Get Itinerary
```
GET /api/itineraries/<id>/
Authorization: Token <your_token>
```

### Update Itinerary
```
PUT /api/itineraries/<id>/
Authorization: Token <your_token>
```

### Delete Itinerary
```
DELETE /api/itineraries/<id>/
Authorization: Token <your_token>
```

---

## Error Responses

| Status | Meaning |
|--------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created |
| 204 | No Content - Delete successful |
| 400 | Bad Request - Invalid data |
| 401 | Unauthorized - Token required or invalid |
| 403 | Forbidden - Admin only endpoint |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limited |

---

## Testing in Browser

1. Start server: `python manage.py runserver`
2. Visit: `http://localhost:8000/api/docs/`
3. All endpoints listed interactively
4. Click "Try it out" to test any endpoint
