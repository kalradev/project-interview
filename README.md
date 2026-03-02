# Interview Agent (Desktop Setup)

Interview runs in an **installed desktop app** that takes the full screen. The candidate cannot switch to other apps; leaving the window triggers a warning, then disqualification. Optionally connects to the **interview backend** (`interview/`) to log events (tab_switch) and end sessions.

## How it works

- **Fullscreen + kiosk**: The app opens in fullscreen with no taskbar or window controls.
- **Focus lock**: If the user switches to another app (e.g. Alt+Tab), the window is refocused and the app sends a "left screen" event.
- **Warning / disqualify**: First time leaving = warning modal. Second time = disqualified screen (interview over).

## Development

```bash
npm install
```

**Backend (optional, for event logging):** From project root, start the interview API (requires PostgreSQL and `.env` in `interview/`):

```bash
cd interview && pip install -r requirements.txt && uvicorn app.main:app --reload
```

API: http://localhost:8000 — Docs: http://localhost:8000/docs

**Desktop app:**

**Option A – Build and run the app (loads built files):**
```bash
npm run electron:dev
```

**Option B – Run with live Vite (hot reload):**
```bash
npm run electron:dev:live
```

## Build installer (for candidate’s device)

Creates an installable app in the `release/` folder (e.g. Windows `.exe` installer):

```bash
npm run electron:build
```

- **Windows**: `release/Interview Agent 1.0.0.exe` (NSIS installer). Run it to install; candidate opens "Interview Agent" from Start or desktop.
- **macOS/Linux**: Use the same command; adjust `package.json` `build` section if you need `.dmg` or `.AppImage`.

## Connecting to the interview backend

1. Start the backend (see **Backend** above) and create a session (e.g. via `/api/v1/sessions` with Admin/Interviewer JWT).
2. Open the desktop app. On first run you get a **Setup** screen.
3. Enter **API base URL** (e.g. `http://localhost:8000`), **Session ID** (UUID from the backend), and **Auth token** (JWT from login). Click **Save and start (connected)**.
4. Leave events (tab/window leave) are sent as `tab_switch` to `/api/v1/events/log`. On disqualify, the app also calls `/api/v1/sessions/end` and `/api/v1/integrity/compute/{session_id}`.

To run without the backend, click **Start in standalone mode** on the setup screen.

## Candidate flow

1. Install "Interview Agent" from the installer (or run with `npm run electron:dev`).
2. If using the backend, the interviewer may pre-fill API URL, Session ID, and token; otherwise the candidate sees the setup screen.
3. Open the app → interview runs in fullscreen.
4. Do not switch to other apps or windows; first time = warning, second time = disqualification.

---

## When testing on your own PC: how to get back to Cursor

The app runs in fullscreen and grabs focus. To exit and return to your desktop/Cursor:

- Press **Ctrl+Shift+8**.

This closes the app and returns you to your normal desktop. Do not tell candidates this shortcut so they cannot use it during a real interview.
