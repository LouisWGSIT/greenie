#!/usr/bin/env node
// Creates the tray icon at startup if it doesn't exist
const fs = require('fs');
const path = require('path');

// Base64 encoded small green icon (16x16 green square with chat bubble)
const ICON_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAA+0lEQVR4nGNgYGD4/5+BgYGBkYGBgZGRgeE/AwPDf0YGhv8MDAwMDAwMDAwMDAwMzMzMzMyMjEwM/xkYGP4zMDAwMjAwMDIyMDAyMDAyMjIyMjMxMjI0M/xjYGRgYGBkZGRkYGRkZGBkYGBgYGBkYGBkYGRgZGBkYGBgYGBkZGRkYGBkYGBkZGRkZGRkYGBgZGBkZGRkYGRkYGRkZGRkZGBgYGRkZGRkZGRkZGBkZGRkZGBgZGRkZGRkZGRkZGBkZGRkZGBkZGRkZGBkZGRkZGRkZGBkZGRkZGBkZGRgYGRkZGRkYGBkZGRkYGBkZGBkYGBkZGBkZGBkZGRkZGRkZGRkZGRkZGRkZGBkZGBkZGRkZGRkZGRkZGRkZGBkZGBkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGBkZGRkZGRkZGRkZGRgYGBgYAG4A46v5qwQQAAAAAElFTkSuQmCC';

const assetsDir = path.join(__dirname, 'assets');
const iconPath = path.join(assetsDir, 'tray-icon.png');

// Create assets directory if it doesn't exist
if (!fs.existsSync(assetsDir)) {
    fs.mkdirSync(assetsDir, { recursive: true });
}

// Create icon file if it doesn't exist
if (!fs.existsSync(iconPath)) {
    const buffer = Buffer.from(ICON_BASE64, 'base64');
    fs.writeFileSync(iconPath, buffer);
    console.log('✓ Tray icon created');
} else {
    console.log('✓ Tray icon already exists');
}
