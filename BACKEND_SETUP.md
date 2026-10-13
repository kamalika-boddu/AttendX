# AttendX – Flask Backend & MySQL Database Setup Guide

This guide details the complete Python Flask backend and MySQL database architecture for AttendX.

---

## 1. Prerequisites

- Python 3.10+ (Current: Python 3.13)
- MySQL Server 8.0+ running on port 3306 (Windows service `MySQL80`)
- Node.js 18+ and npm

---

## 2. Directory Structure

```
SLAM project/
├── backend/
│   ├── app.py              # Flask REST API endpoints & route logic
│   ├── auth_utils.py       # JWT creation, scrypt hashing, @token_required, @roles_required
│   ├── config.py           # Environment variables configuration loader
│   ├── db.py               # PyMySQL connection pool and parameterized execution
│   ├── schema.sql          # MySQL DDL (tables: users, students, sessions, records)
│   ├── seed.sql            # Initial test data (users, students, historical roll calls)
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example        # Sanitized template of configuration variables
│   ├── .env                # Local development credentials (never commit real secrets)
│   ├── test_api.py         # Automated API test suite
│   └── venv/               # Python virtual environment
├── src/
│   ├── api/
│   │   └── attendxApi.js   # Frontend API client with JWT handling
│   ├── components/         # React modules (LoginPage, Dashboard, Students, Attendance, Reports)
│   ├── App.jsx             # Top-level session verification
│   └── index.css           # AttendX styling
├── vite.config.js          # Vite config with proxy: /api -> http://127.0.0.1:5000
└── package.json
```

---

## 3. Database Initialization

Execute the schema and seed scripts using MySQL client:

```powershell
Get-Content backend\schema.sql -Raw | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u user1 -p"user123"
Get-Content backend\seed.sql -Raw | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u user1 -p"user123"
```

---

## 4. Running the Application

### A. Run Flask Backend (Port 5000)
```powershell
backend\venv\Scripts\python.exe backend\app.py
```
Outputs:
`* Running on http://127.0.0.1:5000`

### B. Run React Frontend (Port 3000)
```powershell
npm run dev
```
Outputs:
`Local: http://localhost:3000/`

---

## 5. Automated Tests

Run the backend test suite:
```powershell
backend\venv\Scripts\python.exe backend\test_api.py
```
Verifies:
- Health check
- User registration
- User login with scrypt hash verification
- Current user profile retrieval (`/api/auth/me`)
- Student listing
- Unique student ID validation and insertion
- Duplicate student ID prevention (409 Conflict)
- Student updating
- Roll call marking and transaction upsert
- Report analytics calculations
- Cascading student deletion
