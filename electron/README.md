# Greenie Desktop - Electron App

## Quick Start

### Install Dependencies
```bash
cd electron
npm install
```

### Run Development Version
```bash
npm start
```

### Build Windows Installer
```bash
npm run build:win
```

This creates an installer in `electron/dist/` folder.

## Features

- ✅ Always-on-top overlay
- ✅ System tray integration
- ✅ Floating green button
- ✅ Drag to move
- ✅ Connects to Render backend
- ✅ Auto-login from saved credentials
- ✅ Desktop shortcut on install

## How It Works

1. **Launches minimized to system tray** (green icon in taskbar)
2. **Click tray icon** or press hotkey to show/hide
3. **Floating overlay** stays on top of all windows
4. **Drag from header** to reposition
5. **Minimize button** hides it (doesn't close)
6. **Close button** sends to tray
7. **Right-click tray** for menu options

## API Configuration

Edit `main.js` line 9 to change API URL:
```javascript
const API_URL = 'https://greenie-t89u.onrender.com';
```

## Icon Files Needed

Replace these placeholder files with real icons:
- `assets/tray-icon.png` - 16x16 or 32x32 PNG
- `assets/icon.ico` - Windows app icon

## Building for Production

Windows:
```bash
npm run build:win
```

Output: `dist/Greenie Setup 1.0.0.exe`

## Installation

1. Run the setup.exe
2. Greenie installs and starts automatically
3. Look for green icon in system tray
4. Click to open overlay
5. Sign in with @greensafeit.com email

## Uninstall

Windows: Settings → Apps → Greenie → Uninstall
