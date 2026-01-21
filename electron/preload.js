const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
    getApiUrl: () => ipcRenderer.invoke('get-api-url'),
    minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
    quitApp: () => ipcRenderer.invoke('quit-app')
});
