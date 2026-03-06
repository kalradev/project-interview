const { app, BrowserWindow, globalShortcut, ipcMain, screen } = require('electron')
const path = require('path')
const fs = require('fs')

let mainWindow = null
let allowClose = false // true when user legitimately ends interview and requests close
let interviewMode = false // when true, block copy/cut shortcuts to reduce cheating

function getIconPath() {
  const root = path.join(__dirname, '..')
  // On Windows, .ico often renders more clearly in the title bar than .png
  if (process.platform === 'win32') {
    const publicIco = path.join(root, 'public', 'agent.ico')
    if (fs.existsSync(publicIco)) return publicIco
  }
  const distPng = path.join(root, 'dist', 'agent.png')
  const publicPng = path.join(root, 'public', 'agent.png')
  if (fs.existsSync(distPng)) return distPng
  if (fs.existsSync(publicPng)) return publicPng
  return null
}

function createWindow() {
  allowClose = false
  interviewMode = false
  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  const iconPath = getIconPath()
  mainWindow = new BrowserWindow({
    width,
    height,
    ...(iconPath && { icon: iconPath }),
    fullscreen: false,
    kiosk: false,
    frame: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  mainWindow.setMenu(null)
  mainWindow.setAlwaysOnTop(false)
  mainWindow.setFullScreen(false)

  const useDevServer = process.env.ELECTRON_DEV === '1'
  if (useDevServer) {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.once('ready-to-show', () => mainWindow.show())

  // Block copy/cut and Windows key when in interview mode
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (!interviewMode) return
    const key = (input.key || '').toLowerCase()
    // Block Windows (Super/Meta) key so Start menu doesn't open
    if (key === 'meta' || key === 'super' || input.meta) {
      event.preventDefault()
      return
    }
    if (input.control || input.meta) {
      if (key === 'c' || key === 'x') {
        event.preventDefault()
      }
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  mainWindow.on('close', (event) => {
    if (allowClose) {
      return // allow window to close (user chose "End interview" -> Close)
    }
    // Only block close during the actual interview; on login/setup/photo the user can close the window normally
    if (!interviewMode) {
      return // allow close (e.g. X button on login screen)
    }
    event.preventDefault()
    mainWindow.webContents.send('app-blur') // during interview: first time = warning, then disqualify
  })

  mainWindow.on('blur', () => {
    if (mainWindow.isFullScreen()) {
      mainWindow.webContents.send('app-blur')
      setTimeout(() => {
        if (mainWindow && !mainWindow.isDestroyed()) mainWindow.focus()
      }, 500)
    }
  })
}

function exitFullscreenAndQuit() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.setFullScreen(false)
    mainWindow.setKiosk(false)
    mainWindow.setAlwaysOnTop(false)
    mainWindow.close()
  }
  app.quit()
}

app.whenReady().then(() => {
  createWindow()

  ipcMain.on('enter-interview-mode', () => {
    interviewMode = true
    registerInterviewShortcuts() // block Windows key so Start menu doesn't open
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.setFullScreen(true)
      mainWindow.setKiosk(true)
      mainWindow.setAlwaysOnTop(true, 'screen-saver')
    }
  })

  ipcMain.on('request-close-interview', () => {
    interviewMode = false
    unregisterInterviewShortcuts()
    allowClose = true
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.close()
    }
  })

  try {
    globalShortcut.register('Alt+Tab', () => {})
  } catch (_) {}
  try {
    globalShortcut.register('Super+Tab', () => {})
  } catch (_) {}
  // Escape for testing: press Ctrl+Shift+8 to exit fullscreen and close the app
  try {
    globalShortcut.register('Ctrl+Shift+8', exitFullscreenAndQuit)
  } catch (_) {}
})

// When entering interview mode, block Windows (Super) key so Start menu doesn't open
function registerInterviewShortcuts() {
  try {
    globalShortcut.register('Super', () => {}) // Windows key alone
  } catch (_) {}
}

function unregisterInterviewShortcuts() {
  try {
    globalShortcut.unregister('Super')
  } catch (_) {}
}

app.on('window-all-closed', () => {
  unregisterInterviewShortcuts()
  globalShortcut.unregisterAll()
  app.quit()
})

app.on('activate', () => {
  if (mainWindow === null) createWindow()
})
