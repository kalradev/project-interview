const { app, BrowserWindow, globalShortcut, ipcMain, screen } = require('electron')
const path = require('path')

let mainWindow = null
let allowClose = false // true when user legitimately ends interview and requests close

function createWindow() {
  allowClose = false
  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  mainWindow = new BrowserWindow({
    width,
    height,
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
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.once('ready-to-show', () => mainWindow.show())

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  mainWindow.on('close', (event) => {
    if (allowClose) {
      return // allow window to close (user chose "End interview" -> Close)
    }
    event.preventDefault()
    mainWindow.webContents.send('app-blur') // Alt+F4 or close: first time = warning, second = disqualify
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
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.setFullScreen(true)
      mainWindow.setKiosk(true)
      mainWindow.setAlwaysOnTop(true, 'screen-saver')
    }
  })

  ipcMain.on('request-close-interview', () => {
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

app.on('window-all-closed', () => {
  globalShortcut.unregisterAll()
  app.quit()
})

app.on('activate', () => {
  if (mainWindow === null) createWindow()
})
