/**
 * Remove the release folder before electron-builder runs.
 * If something is using the folder (e.g. Interview Agent is open), removal fails
 * and we exit with a clear message so the user closes the app and runs build again.
 */
const fs = require('fs');
const path = require('path');

const releaseDir = path.join(__dirname, '..', 'release');

if (!fs.existsSync(releaseDir)) {
  process.exit(0);
  return;
}

try {
  fs.rmSync(releaseDir, { recursive: true, force: true });
} catch (err) {
  console.error('');
  console.error('Could not remove the "release" folder (a file is in use).');
  console.error('  → Close the Interview Agent app and any File Explorer window in that folder.');
  console.error('  → Then run: npm run electron:build');
  console.error('');
  process.exit(1);
}
