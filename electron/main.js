const { app, BrowserWindow, Tray, Menu, ipcMain, screen } = require('electron');
const path = require('path');

let mainWindow = null;
let tray = null;
let isQuitting = false;

// API URL - change this after deploying
const API_URL = 'https://greenie-t89u.onrender.com';

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

    // Start minimized
    mainWindow.hide();
}

function createTray() {
    // Use a simple icon for now (you can replace with a proper .ico file)
    tray = new Tray(path.join(__dirname, 'assets', 'tray-icon.png'));
    
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
