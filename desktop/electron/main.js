const { app, BrowserWindow, Tray, Menu, nativeImage, ipcMain } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const API_BASE = "http://127.0.0.1:8420";
let mainWindow;
let overlayWindow;
let tray;
let backend;
let backendStatus = { running: false, pid: null, lastError: null, mode: "external-or-starting" };

function repoRoot() {
  if (app.isPackaged) return path.dirname(process.execPath);
  return path.resolve(__dirname, "..", "..");
}

function pythonPath() {
  const roots = [
    repoRoot(),
    process.resourcesPath || repoRoot()
  ];
  for (const root of roots) {
    const candidate = path.join(root, "venv", "Scripts", "python.exe");
    if (fs.existsSync(candidate)) return candidate;
    const bundled = path.join(root, "python", "python.exe");
    if (fs.existsSync(bundled)) return bundled;
  }
  return "python";
}

function backendCwd() {
  if (!app.isPackaged) return repoRoot();
  const resourcePython = path.join(process.resourcesPath, "python");
  return fs.existsSync(resourcePython) ? resourcePython : repoRoot();
}

async function isApiHealthy() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

async function ensureBackend() {
  if (await isApiHealthy()) {
    backendStatus = { running: true, pid: null, lastError: null, mode: "external" };
    return;
  }

  backend = spawn(pythonPath(), ["-m", "cogn_os.api.server"], {
    cwd: backendCwd(),
    env: {
      ...process.env,
      PYTHONPATH: path.join(backendCwd(), "src"),
      COGNOS_API_HOST: "127.0.0.1",
      COGNOS_API_PORT: "8420"
    },
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"]
  });

  backendStatus = { running: true, pid: backend.pid, lastError: null, mode: "managed" };

  backend.stderr.on("data", (chunk) => {
    const text = chunk.toString();
    if (/error|exception|traceback/i.test(text)) backendStatus.lastError = text.slice(-1000);
  });

  backend.on("exit", (code) => {
    backendStatus = { running: false, pid: null, lastError: `Backend exited with code ${code}`, mode: "managed" };
    updateTray();
  });

  for (let i = 0; i < 40; i++) {
    if (await isApiHealthy()) return;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  backendStatus.lastError = "Backend did not become healthy within 20 seconds.";
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 920,
    minHeight: 620,
    title: "CognOS",
    backgroundColor: "#0f1115",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  const devUrl = process.env.VITE_DEV_SERVER_URL || "http://127.0.0.1:5173";
  const prod = `file://${path.join(__dirname, "../dist/index.html")}`;
  mainWindow.loadURL(app.isPackaged ? prod : devUrl);
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.on("close", (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

function createOverlayWindow() {
  overlayWindow = new BrowserWindow({
    width: 360,
    height: 420,
    minWidth: 320,
    minHeight: 260,
    title: "CognOS Overlay",
    frame: false,
    transparent: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    backgroundColor: "#11151d",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  const devUrl = process.env.VITE_DEV_SERVER_URL || "http://127.0.0.1:5173";
  const prod = `file://${path.join(__dirname, "../dist/index.html")}`;
  overlayWindow.loadURL(`${app.isPackaged ? prod : devUrl}#overlay`);
}

function updateTray() {
  if (!tray) return;
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: backendStatus.running ? "CognOS: Running" : "CognOS: Stopped", enabled: false },
    { label: "Open CognOS", click: () => { mainWindow.show(); mainWindow.focus(); } },
    { label: "Toggle Overlay", click: () => toggleOverlay() },
    { label: "Hide", click: () => mainWindow.hide() },
    { type: "separator" },
    { label: "Quit", click: () => { app.isQuitting = true; app.quit(); } }
  ]));
}

ipcMain.handle("backend-status", () => backendStatus);
ipcMain.handle("toggle-overlay", () => toggleOverlay());

function toggleOverlay() {
  if (!overlayWindow) createOverlayWindow();
  if (overlayWindow.isVisible()) {
    overlayWindow.hide();
    return false;
  }
  const display = require("electron").screen.getPrimaryDisplay().workArea;
  overlayWindow.setPosition(display.x + display.width - 390, display.y + 80);
  overlayWindow.show();
  return true;
}

app.whenReady().then(async () => {
  await ensureBackend();
  createWindow();
  createOverlayWindow();
  tray = new Tray(nativeImage.createEmpty());
  tray.setToolTip("CognOS");
  updateTray();
});

app.on("before-quit", () => {
  app.isQuitting = true;
  if (backend && backendStatus.mode === "managed") backend.kill();
});

app.on("window-all-closed", (event) => {
  event.preventDefault();
  if (mainWindow) mainWindow.hide();
});
