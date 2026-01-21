const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
    getApiUrl: async () => {
        try {
            const url = await ipcRenderer.invoke('get-api-url');
            console.log('[Preload] API URL retrieved:', url);
            return url;
        } catch (err) {
            console.error('[Preload] Failed to get API URL:', err);
            // Fallback to Render backend
            return 'https://greenie-t89u.onrender.com';
        }
    },
    minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
    quitApp: () => ipcRenderer.invoke('quit-app'),
    checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
    onUpdateAvailable: (callback) => ipcRenderer.on('update-available', callback),
    onUpdateDownloaded: (callback) => ipcRenderer.on('update-downloaded', callback)
});