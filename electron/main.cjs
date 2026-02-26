const { app, BrowserWindow, globalShortcut, screen } = require('electron')
const path = require('path')

let mainWindow = null

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  mainWindow = new BrowserWindow({
    width,
    height,
    fullscreen: true,
    kiosk: true,
    frame: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  mainWindow.setMenu(null)
  mainWindow.setAlwaysOnTop(true, 'screen-saver')
  mainWindow.setFullScreen(true)

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
    event.preventDefault()
    mainWindow.webContents.send('app-blur')
  })

  mainWindow.on('blur', () => {
    mainWindow.webContents.send('app-blur')
    setTimeout(() => {
      if (mainWindow && !mainWindow.isDestroyed()) mainWindow.focus()
    }, 500)
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
