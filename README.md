# Interview Agent (Desktop Setup)

Interview runs in an **installed desktop app** that takes the full screen. The candidate cannot switch to other apps; leaving the window triggers a warning, then disqualification.

## How it works

- **Fullscreen + kiosk**: The app opens in fullscreen with no taskbar or window controls.
- **Focus lock**: If the user switches to another app (e.g. Alt+Tab), the window is refocused and the app sends a "left screen" event.
- **Warning / disqualify**: First time leaving = warning modal. Second time = disqualified screen (interview over).

## Development

```bash
npm install
```

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

## Candidate flow

1. Install "Interview Agent" from the installer.
2. Open the app → interview runs in fullscreen.
3. Do not switch to other apps or windows; first time = warning, second time = disqualification.

---

## When testing on your own PC: how to get back to Cursor

The app runs in fullscreen and grabs focus. To exit and return to your desktop/Cursor:

- Press **Ctrl+Shift+8**.

This closes the app and returns you to your normal desktop. Do not tell candidates this shortcut so they cannot use it during a real interview.
