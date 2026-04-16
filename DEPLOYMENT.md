# RepoScope AI — Deployment Guide

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | ≥ 3.11 | https://python.org |
| Node.js | ≥ 20 LTS | https://nodejs.org |
| npm | ≥ 10 | bundled with Node |
| PM2 | latest | `npm i -g pm2` |
| Git | any | https://git-scm.com |

---

## 1 — MongoDB Atlas Setup

1. Go to https://cloud.mongodb.com and create a free account.
2. Create a new **Shared (M0 free)** cluster. Choose a region close to you.
3. In **Database Access** → Add a database user with username/password auth. Note the credentials.
4. In **Network Access** → Add IP `0.0.0.0/0` (allow all) for dev, or your server IP for production.
5. Click **Connect** on your cluster → **Connect your application** → copy the connection string.

   It looks like:
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
6. Replace `<username>` and `<password>` with your credentials.

---

## 2 — Groq API Key

1. Sign up at https://console.groq.com
2. Go to **API Keys** → Create a new key.
3. Copy the key (starts with `gsk_`).

---

## 3 — GitHub Token (Optional but Recommended)

A personal access token prevents GitHub rate-limiting on ZIP downloads.

1. GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic).
2. Generate a token with `public_repo` scope.
3. Copy it.

---

## 4 — Backend Setup

```bash
cd reposcope-ai/backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `backend/.env`:
```env
MONGODB_URI=mongodb+srv://youruser:yourpassword@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DB_NAME=reposcope
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx   # optional
CORS_ORIGINS=http://localhost:5173
```

Test the server:
```bash
python main.py
# Expected: INFO: Application startup complete.
# Visit: http://localhost:8000/api/v1/health
```

---

## 5 — Frontend Setup

```bash
cd reposcope-ai/frontend

npm install

# Development server
npm run dev
# Visit: http://localhost:5173
```

---

## 6 — Running with PM2 (Production)

### Build the frontend first
```bash
cd reposcope-ai/frontend
npm run build
```

### Create logs directory
```bash
mkdir -p reposcope-ai/logs
```

### Start all services
```bash
cd reposcope-ai
pm2 start ecosystem.config.cjs
```

### Useful PM2 commands
```bash
pm2 status                          # check processes
pm2 logs reposcope-backend          # backend logs
pm2 logs reposcope-frontend         # frontend logs
pm2 restart reposcope-backend       # restart backend
pm2 stop all                        # stop everything
pm2 save && pm2 startup             # auto-start on reboot
```

---

## 7 — Systemd Alternative (Linux)

### Backend service

Create `/etc/systemd/system/reposcope-backend.service`:
```ini
[Unit]
Description=RepoScope AI Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/reposcope-ai/backend
EnvironmentFile=/opt/reposcope-ai/backend/.env
ExecStart=/opt/reposcope-ai/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable reposcope-backend
systemctl start reposcope-backend
systemctl status reposcope-backend
```

---

## 8 — Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | ✅ | MongoDB Atlas connection string |
| `DB_NAME` | No | Database name (default: `reposcope`) |
| `GROQ_API_KEY` | ✅ | Groq API key for Llama-3 |
| `GITHUB_TOKEN` | Recommended | GitHub PAT to avoid rate limits |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |

---

## 9 — Application URLs

| Service | URL |
|---------|-----|
| Frontend (dev) | http://localhost:5173 |
| Frontend (prod/PM2) | http://localhost:4173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/v1/health |

---

## 10 — Troubleshooting

**`ModuleNotFoundError`** — Ensure the venv is activated: `source .venv/bin/activate`

**`MongoServerError: Authentication failed`** — Double-check username/password in `MONGODB_URI`. Avoid special characters; URL-encode them if present.

**`httpx.HTTPStatusError: 404`** — The branch name is wrong. Try `master` instead of `main`.

**`groq.APIConnectionError`** — Check `GROQ_API_KEY` is correct and not expired.

**React Flow shows blank canvas** — Open browser console; check if `/api/v1/graph/<id>` is returning 200. Ensure the Vite proxy is configured correctly.
