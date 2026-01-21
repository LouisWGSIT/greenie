const { app, BrowserWindow, Tray, Menu, ipcMain, screen, nativeImage } = require('electron');
const path = require('path');
const { autoUpdater } = require('electron-updater');

let mainWindow = null;
let tray = null;
let isQuitting = false;

// API URL - change this after deploying
const API_URL = 'https://greenie-t89u.onrender.com';

// Configure auto-updater
autoUpdater.checkForUpdatesAndNotify();

// Ensure only one instance runs
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        if (mainWindow) {
            mainWindow.show();
        }
    });
}

function createWindow() {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;
    
    mainWindow = new BrowserWindow({
        width: 400,
        height: 600,
        x: width - 420, // Position on right side
        y: height - 620, // Position at bottom
        frame: false, // No window frame
        transparent: true, // Transparent background
        alwaysOnTop: true, // Always stay on top
        skipTaskbar: true, // Don't show in taskbar
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        }
    });

    mainWindow.loadFile('overlay.html');
    
    // Hide instead of close
    mainWindow.on('close', (event) => {
        if (!isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });

    // Show window on startup
    mainWindow.show();
}

function createTray() {
    try {
        // Load Windows ICO for crisp tray icon
        const iconPath = path.join(__dirname, 'assets', 'icon.ico');
        const icon = nativeImage.createFromPath(iconPath);
        icon.setTemplateImage(false);
        tray = new Tray(icon);
    } catch (err) {
        console.warn('Could not load tray icon:', err.message);
        // Final fallback - create simple nativeImage
        try {
            const img = nativeImage.createEmpty();
            img.addRepresentation({
                scaleFactor: 1.0,
                width: 16,
                height: 16,
                buffer: Buffer.alloc(16 * 16 * 4, 0x00ff0080)
            });
            tray = new Tray(img);
        } catch (e) {
            console.error('Failed to create tray:', e.message);
            return;
        }
    }
    
    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Show Greenie',
            click: () => {
                mainWindow.show();
            }
        },
        {
            label: 'Hide Greenie',
            click: () => {
                mainWindow.hide();
            }
        },
        { type: 'separator' },
        {
            label: 'Check for Updates',
            click: () => {
                autoUpdater.checkForUpdates();
            }
        },
        { type: 'separator' },
        {
            label: 'Settings',
            click: () => {
                // Future: Open settings window
            }
        },
        { type: 'separator' },
        {
            label: 'Quit Greenie',
            click: () => {
                isQuitting = true;
                app.quit();
            }
        }
    ]);

    tray.setToolTip('Greenie - AI Assistant');
    tray.setContextMenu(contextMenu);
    
    // Show/hide on tray click
    tray.on('click', () => {
        if (mainWindow.isVisible()) {
            mainWindow.hide();
        } else {
            mainWindow.show();
        }
    });
}

// App ready
app.whenReady().then(() => {
    createWindow();
    createTray();
    
    // Check for updates every hour
    setInterval(() => {
        autoUpdater.checkForUpdates();
    }, 60 * 60 * 1000);
    
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

// Quit when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Auto-updater events
autoUpdater.on('update-available', () => {
    console.log('Update available');
    mainWindow.webContents.send('update-available');
});

autoUpdater.on('update-not-available', () => {
    console.log('No updates available');
});

autoUpdater.on('update-downloaded', () => {
    console.log('Update downloaded, will install on quit');
    mainWindow.webContents.send('update-downloaded');
    // Auto-install on quit
    autoUpdater.quitAndInstall();
});

// IPC handlers for communication with renderer
ipcMain.handle('get-api-url', () => {
    return API_URL;
});

ipcMain.handle('minimize-window', () => {
    mainWindow.hide();
});

ipcMain.handle('quit-app', () => {
    isQuitting = true;
    app.quit();
});

ipcMain.handle('check-for-updates', async () => {
    const result = await autoUpdater.checkForUpdates();
    return {
        updateAvailable: result.updateInfo.version !== app.getVersion(),
        currentVersion: app.getVersion(),
        availableVersion: result.updateInfo.version
    };
});
