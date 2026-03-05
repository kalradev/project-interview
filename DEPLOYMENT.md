# Deployment Guide

Step-by-step guide to deploy the Interview Integrity Agent for production or market testing.

**You do not need a custom domain.** Use the free URLs from each platform (e.g. `*.railway.app`, `*.vercel.app`, `*.netlify.app`, GitHub Releases).

---

## Deploy without a domain (quick path)

1. **Backend:** Deploy `interview/` to **Railway** or **Render** → you get e.g. `https://your-project.railway.app`.
2. **Dashboard:** Deploy `admin-dashboard/` to **Vercel** or **Netlify** → you get e.g. `https://your-project.vercel.app`.
3. **Backend env:** Set `CORS_ORIGINS=https://your-project.vercel.app` (your actual dashboard URL). Set `SECRET_KEY`, `POSTGRES_*`, etc.
4. **Dashboard build:** Set `VITE_API_URL=https://your-project.railway.app` (your actual API URL), then build and deploy.
5. **Electron:** Build with `VITE_API_URL=https://your-project.railway.app npm run electron:build`; upload the `.exe` to **GitHub Releases** or a file host and share the link.

Share the dashboard URL with admins and the installer link with candidates. No domain or DNS required.

---

## Overview

| Component | What it is | Where to deploy |
|-----------|------------|-----------------|
| **Backend (API)** | FastAPI app in `interview/` | Railway, Render, Fly.io, or a VPS |
| **Admin dashboard** | React app in `admin-dashboard/` | Vercel, Netlify, or your server |
| **Electron app** | Desktop app for candidates (root + `electron/`) | Build installers; share download link |

**User flow**

- **Admins:** Open dashboard URL in browser → sign up / log in → add candidates, send invites. No install.
- **Candidates:** Download installer from your link → install → open app → enter API URL (or use pre-filled) → log in with invite credentials.

---

## 1. Deploy the backend (API)

### 1.1 Prepare environment

```bash
cd interview
cp .env.example .env
# Edit .env with real values (see below).
```

**Required in `.env` for production:**

| Variable | Description |
|----------|-------------|
| `DEBUG` | `false` |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | Your dashboard URL (no domain needed), e.g. `https://your-project.vercel.app` |
| `SECRET_KEY` | Long random string (e.g. `openssl rand -hex 32`). **Never use the default.** |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Your PostgreSQL connection details |
| `OPENAI_API_KEY` | If you use AI interview questions |

**Optional:** Email (Brevo or SMTP), `SETUP_APP_DOWNLOAD_URL` (link to installer for invite emails).

### 1.2 Deploy to a host

**Option A – Railway**

1. Create a project, add PostgreSQL from the catalog.
2. Add a new service from the `interview/` directory (or connect GitHub repo and set root to `interview`).
3. In Variables, set all vars from `.env` (Railway exposes `DATABASE_URL` from PostgreSQL; you can keep `POSTGRES_*` or map from `DATABASE_URL` if your app supports it).
4. Set `CORS_ORIGINS` to your dashboard URL (no domain needed, e.g. `https://your-project.vercel.app`).
5. Deploy. Note the public URL (e.g. `https://your-project.railway.app`).

**Option B – Render**

1. New Web Service, connect repo, root directory: `interview`.
2. Build: `pip install -r requirements.txt` (or your install command).
3. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Add PostgreSQL from Render dashboard; set env vars including `CORS_ORIGINS`.

**Option C – VPS (e.g. Ubuntu)**

1. Install Python, PostgreSQL, Nginx (reverse proxy).
2. Clone repo, create venv, install deps, copy `.env` and fill it.
3. Run with gunicorn/uvicorn behind Nginx; use certbot for HTTPS.

### 1.3 Database

- Ensure PostgreSQL is running and reachable.
- Create the schema (e.g. run your migrations or `python -m scripts.create_schema` from `interview/`).
- Optionally seed the first admin: `python -m scripts.seed_admin` or use dashboard signup when no users exist.

### 1.4 Health check

```bash
curl https://your-api-url/health
# Expected: {"status":"ok"}
```

---

## 2. Deploy the admin dashboard

### 2.1 Build with production API URL

Set your deployed backend URL at build time:

```bash
cd admin-dashboard
cp .env.example .env
# Set in .env (no domain needed – use your backend’s platform URL):
# VITE_API_URL=https://your-project.railway.app
# (no trailing slash)

npm run build
```

Or one-off:

```bash
VITE_API_URL=https://your-project.railway.app npm run build
```

Output is in `admin-dashboard/dist/`.

### 2.2 Deploy the built files

**Option A – Vercel**

1. Connect the repo; set root directory to `admin-dashboard`.
2. Build command: `npm run build`.
3. Output directory: `dist`.
4. Environment variable: `VITE_API_URL` = your backend URL (e.g. `https://your-project.railway.app`).
5. Deploy. Note the dashboard URL (e.g. `https://your-project.vercel.app`).

**Option B – Netlify**

1. Connect repo; base directory: `admin-dashboard`.
2. Build command: `npm run build`; publish directory: `dist`.
3. Add env var `VITE_API_URL` = your backend URL.
4. Deploy.

**Option C – Your server**

- Serve the contents of `admin-dashboard/dist/` with Nginx/Apache (or any static host) over HTTPS.

### 2.3 CORS

- In the **backend** env, set `CORS_ORIGINS` to the **exact** dashboard origin (no domain needed, e.g. `https://your-project.vercel.app`).
- Restart the backend so CORS allows the dashboard.

---

## 3. Build and distribute the Electron app (for candidates)

### 3.1 Build with production API URL (optional but recommended)

So the app opens with the API URL already set:

```bash
# From project root (where package.json has electron:build)
VITE_API_URL=https://your-project.railway.app npm run electron:build
```

If you omit `VITE_API_URL`, candidates can still type the API URL on the login screen.

### 3.2 Installer output

- Windows: `release/Interview Agent Setup x.x.x.exe` (or similar).
- macOS: build on a Mac for `.dmg`/`.app`.

### 3.3 Share the installer (no domain needed)

- **GitHub Releases:** Create a release, attach the `.exe` (and `.dmg` if applicable). Share the release URL (e.g. `https://github.com/your-username/your-repo/releases/latest`).
- **Cloud storage:** Google Drive, Dropbox, OneDrive – upload the installer and share a download link.
- **Optional:** If you have a server/domain, you can host the file there and share that URL instead.

### 3.4 Invite emails (optional)

- In backend `.env`, set `SETUP_APP_DOWNLOAD_URL` to the installer (or a landing page that links to it).
- When admins add candidates and send invite email, the email can include this link so candidates know where to download the app.

---

## 4. Quick checklist before go-live

- [ ] Backend: `SECRET_KEY` changed from default; `DEBUG=false`; `CORS_ORIGINS` set to dashboard URL.
- [ ] Backend: PostgreSQL configured and schema created.
- [ ] Dashboard: Built with `VITE_API_URL` pointing to the deployed API.
- [ ] Dashboard URL added to backend `CORS_ORIGINS`.
- [ ] Electron: Built (with `VITE_API_URL` for pre-filled API URL if desired); installer uploaded and link ready.
- [ ] HTTPS used for both API and dashboard in production.
- [ ] First admin: signed up via dashboard (when no users exist) or seeded via script.

---

## 5. How users “install” and use

| Role | What they get | What they do |
|------|----------------|--------------|
| **Admin** | Dashboard URL (the Vercel/Netlify URL you get – no domain needed) | Open URL in browser → Sign up (first user) or Log in → Add candidates, send invites. No install. |
| **Candidate** | Invite email with credentials + (optionally) download link (e.g. GitHub Releases – no domain needed) | Download installer → Run and install → Open app → API URL can be pre-filled or they enter it once → Log in with email + password from invite. |

After deployment, share the **dashboard link** with admins and the **installer link** with candidates so they can test in the market.
