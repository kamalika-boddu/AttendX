# AttendX – Cloud Deployment Architecture & Runbook

This guide details the production deployment strategy for **AttendX – Cloud-Based Attendance Management System**, including recommendations, step-by-step instructions, security hardening, backups, and cost breakdowns.

---

## 1. Recommended Hosting Architectures

### Architecture Comparison Matrix

| Option | Frontend Hosting | Backend API Hosting | Database Hosting | Monthly Cost | Ideal For |
|---|---|---|---|---|---|
| **Option A (Recommended)** | **Vercel** / **Netlify** | **Render** / **Railway** | **Aiven for MySQL** / **Railway MySQL** | **$0 / month** (Free tier) | College projects, portfolios, student evaluations |
| **Option B (All-in-One PaaS)** | **Render Static Site** | **Render Web Service** | **Render Managed PostgreSQL / Aiven** | **$0 - $7 / month** | Simplified single-dashboard deployment |
| **Option C (Cloud VPS / VM)** | **Nginx** (Same VPS) | **Gunicorn** + **Systemd** | **MySQL 8.0** (Local/Managed) | **$4 - $6 / month** (DigitalOcean / AWS Lightsail) | Production systems requiring dedicated compute |

---

## 2. Option A: Step-by-Step Free-Tier Deployment (Recommended)

### Step 1: Managed MySQL Database (Aiven / Railway)
1. **Create Database**:
   - Go to [Aiven.io](https://aiven.io/) or [Railway.app](https://railway.app/).
   - Select **MySQL 8.0** (Free Tier / Starter plan).
   - Choose a region close to your target users (e.g. `ap-south-1` Mumbai or `us-east-1` N. Virginia).
2. **Retrieve Connection String & Credentials**:
   - Copy the URI: `mysql://<username>:<password>@<host>:<port>/<dbname>?ssl-mode=REQUIRED`
   - Or record separate values: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_SSL=true`.
3. **Initialize Schema & Seed Data**:
   From your local terminal, run the provided SQL scripts against the cloud database:
   ```bash
   mysql -h <host> -P <port> -u <user> -p<password> <dbname> < backend/schema.sql
   mysql -h <host> -P <port> -u <user> -p<password> <dbname> < backend/seed.sql
   ```
4. **Security & Backups**:
   - Aiven and Railway automatically include daily automated backups and point-in-time recovery on free/hobby tiers.
   - Restrict incoming connections using IP whitelist rules if your backend IP is static.

---

### Step 2: Deploy Flask REST API (Render / Railway)
1. **Push Code to GitHub**:
   Ensure `.env` is **not** committed (verified by `.gitignore`).
2. **Create Web Service on Render**:
   - Go to [Render.com](https://render.com/) -> **New** -> **Web Service**.
   - Connect your GitHub repository.
   - Set **Root Directory**: `backend`
   - Set **Runtime**: `Python 3`
   - Set **Build Command**: `pip install -r requirements.txt`
   - Set **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 60`
3. **Configure Environment Variables in Render Dashboard**:
   | Variable | Value | Notes |
   |---|---|---|
   | `FLASK_ENV` | `production` | Disables debug mode |
   | `FLASK_DEBUG` | `0` | Secure in production |
   | `SECRET_KEY` | *(Generate 32+ random chars)* | Session cryptography |
   | `JWT_SECRET` | *(Generate 64+ random chars)* | HS256 JWT signing key |
   | `JWT_EXPIRATION_HOURS` | `24` | Token lifetime |
   | `DATABASE_URL` | `mysql://user:pass@host:port/dbname` | From Step 1 |
   | `DB_SSL` | `true` | Required for cloud databases |
   | `CORS_ORIGINS` | `https://<your-frontend>.vercel.app` | Updated after Step 3 |
4. **Deploy**:
   - Click **Create Web Service**.
   - Once deployed, copy your backend URL: e.g. `https://attendx-api.onrender.com`.
   - Test health endpoint: `https://attendx-api.onrender.com/api/health` -> `{"status": "healthy"}`.

---

### Step 3: Deploy Frontend (Vercel / Netlify)
1. **Import Repository on Vercel**:
   - Go to [Vercel.com](https://vercel.com/) -> **Add New Project**.
   - Select your AttendX repository.
   - Framework Preset: **Vite** (auto-detected).
   - Root Directory: `./`
   - Build Command: `npm run build`
   - Output Directory: `dist`
2. **Configure Environment Variable**:
   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://attendx-api.onrender.com/api` |
3. **Deploy**:
   - Click **Deploy**. Vercel will build the frontend and provide an SSL-secured HTTPS URL: e.g. `https://attendx.vercel.app`.
4. **Update Backend CORS**:
   - Return to Render, add `https://attendx.vercel.app` to `CORS_ORIGINS`.

---

## 3. Security Hardening & Best Practices

1. **Secrets Management**:
   - Never commit `.env` or password files. All production secrets reside in cloud dashboard environment variables.
2. **HTTPS / TLS Encryption**:
   - Both Vercel and Render enforce HTTPS with automatic Let's Encrypt SSL certificates.
   - HTTP requests are automatically redirected to HTTPS.
   - Responses include `Strict-Transport-Security: max-age=31536000; includeSubDomains`.
3. **JWT Authentication Security**:
   - Tokens are signed with HMAC-SHA256 using a 64+ character secret.
   - Sent via standard `Authorization: Bearer <token>` HTTP headers.
   - Scrypt password hashing prevents rainbow-table and brute-force attacks.
4. **Database Access Restriction**:
   - Managed cloud databases require TLS/SSL connections.
   - Database credentials are kept in server environment variables.
   - Parameterized queries eliminate SQL injection vulnerabilities.

---

## 4. Free-Tier Limitations & Pricing Breakdown

| Provider | Service | Free Tier Allowances | Potential Limitations |
|---|---|---|---|
| **Vercel** | Frontend Static Host | 100 GB bandwidth/month, unlimited builds, free SSL | None for educational/college workloads. |
| **Render** | Flask API Backend | 750 free instance hours/month | Free instances spin down after 15 mins of inactivity. First request takes ~45 seconds to wake up. (Upgrade to Starter is $7/mo for zero sleep). |
| **Aiven / Railway** | Managed MySQL | 1 CPU, 5 GB storage, automated daily backups | Free credits on Railway are $5/month. Aiven provides free tier clusters with SSL. |

---

## 5. Post-Deployment Verification Checklist

Once deployed to your chosen cloud accounts:

- [ ] **Health Check**: Open `https://<backend-url>/api/health` and verify `{"status": "healthy", "database": "connected"}`.
- [ ] **Frontend Loading**: Open `https://<frontend-url>` and verify the dark navy / cyan theme renders cleanly.
- [ ] **User Registration**: Register a new teacher account and verify the token issues.
- [ ] **Login & Persistence**: Log in with demo credentials (`teacher@attendx.edu` / `teacher123`) and verify redirect to dashboard.
- [ ] **Student CRUD**: Add a student, edit their section, and verify persistence in MySQL.
- [ ] **Mark Attendance**: Take roll call for a class and click Save Attendance. Reload to verify records persist across sessions.
- [ ] **Attendance Reports**: Verify percentages and SVG charts calculate dynamically from the cloud database.
- [ ] **CSV Export**: Click Export to CSV and verify file download over HTTPS.
