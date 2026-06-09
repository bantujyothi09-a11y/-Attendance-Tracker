# Attendance Tracker API Specification

## REST API Endpoints
### Authentication
- `POST /api/auth/login` - Authenticate user credentials.
- `POST /api/auth/logout` - End user session.
- `POST /api/auth/reset-password` - Trigger password reset flow.

### Students
- `GET /api/students` - List students with optional filters.
- `GET /api/students/{id}` - Get a student profile.
- `POST /api/students` - Create a new student.
- `PUT /api/students/{id}` - Update an existing student.
- `DELETE /api/students/{id}` - Archive or delete a student.

### Attendance
- `GET /api/attendance` - Retrieve attendance records.
- `POST /api/attendance` - Create attendance entries.
- `PUT /api/attendance/{id}` - Update a record.
- `DELETE /api/attendance/{id}` - Remove an attendance entry.

### Reports
- `GET /api/reports/attendance-summary` - Summary metrics by date or class.
- `GET /api/reports/student/{id}` - Student attendance report.
- `GET /api/reports/class` - Class-level attendance report.

### Users
- `GET /api/users` - List users (Admin only).
- `POST /api/users` - Create a user.
- `PUT /api/users/{id}` - Update a user.
- `DELETE /api/users/{id}` - Deactivate a user.

## Request / Response Examples
### Login Request
```json
POST /api/auth/login
{
  "username": "adminuser",
  "password": "SecurePassword123"
}
```
### Login Response
```json
200 OK
{
  "token": "eyJ...",
  "user": {
    "id": "1",
    "username": "adminuser",
    "role": "Admin"
  }
}
```
### Create Student Request
```json
POST /api/students
{
  "first_name": "Amina",
  "last_name": "Smith",
  "roll_number": "ST2026-001",
  "class": "Grade 10",
  "section": "A",
  "contact_number": "+1234567890",
  "email": "amina.smith@example.com"
}
```
### Create Student Response
```json
201 Created
{
  "id": "1001",
  "first_name": "Amina",
  "last_name": "Smith",
  "roll_number": "ST2026-001",
  "class": "Grade 10",
  "section": "A",
  "status": "Active"
}
```

## Authentication Requirements
- All API endpoints require authentication except `/api/auth/login` and `/api/auth/reset-password`.
- Access tokens or session cookies must be sent with each request.
- Role-based restrictions apply: Admin-only endpoints must reject Teacher access.
- Passwords are never returned in API responses.

## Error Handling
- `400 Bad Request` for invalid input or missing required fields.
- `401 Unauthorized` for missing or invalid authentication.
- `403 Forbidden` for insufficient permissions.
- `404 Not Found` when resources do not exist.
- `409 Conflict` for duplicate attendance or unique field violations.
- `500 Internal Server Error` for unexpected server failures.

### Error Response Example
```json
400 Bad Request
{
  "error": "ValidationFailed",
  "message": "The roll_number field is required."
}
```
