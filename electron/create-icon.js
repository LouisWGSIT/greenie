// This script creates a simple green icon for the system tray
const { createCanvas } = require('canvas');
const fs = require('fs');
const path = require('path');

// Create a 256x256 green circle (will be scaled down by OS for tray)
const canvas = createCanvas(256, 256);
const ctx = canvas.getContext('2d');

// Green background
ctx.fillStyle = '#00ff00';
ctx.beginPath();
ctx.arc(128, 128, 120, 0, Math.PI * 2);
ctx.fill();

// Dark border
ctx.strokeStyle = '#00cc00';
ctx.lineWidth = 4;
ctx.stroke();

// White chat bubble emoji style
ctx.fillStyle = 'white';
ctx.font = 'bold 180px Arial';
ctx.textAlign = 'center';
ctx.textBaseline = 'middle';
ctx.fillText('💬', 128, 135);

// Save the image
const buffer = canvas.toBuffer('image/png');
const iconPath = path.join(__dirname, 'assets', 'tray-icon.png');

fs.mkdirSync(path.dirname(iconPath), { recursive: true });
fs.writeFileSync(iconPath, buffer);

console.log('✓ Tray icon created at:', iconPath);
