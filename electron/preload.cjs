const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  onAppBlur: (fn) => {
    ipcRenderer.on('app-blur', () => fn())
  },
})
