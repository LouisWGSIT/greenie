const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
    getApiUrl: () => ipcRenderer.invoke('get-api-url'),
    minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
    quitApp: () => ipcRenderer.invoke('quit-app'),
    checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
    onUpdateAvailable: (callback) => ipcRenderer.on('update-available', callback),
    onUpdateDownloaded: (callback) => ipcRenderer.on('update-downloaded', callback)
