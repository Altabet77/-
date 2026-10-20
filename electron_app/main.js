const { app, BrowserWindow, Tray, Menu, nativeImage, ipcMain, shell, session } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const http = require('http');
const fs = require('fs');

// ─── Constants ───────────────────────────────────────────────────────────────
const PORT = 8000;
const SERVER_URL = `http://localhost:${PORT}`;
const BASE_DIR = path.join(__dirname, '..');
const CORE_DIR = path.join(BASE_DIR, 'core_server');
const ICON_PATH = path.join(BASE_DIR, 'samir.ico');
const VENV_PYTHON = path.join(CORE_DIR, '.venv', 'Scripts', 'python.exe');
const RUN_SERVER = path.join(CORE_DIR, 'run_server.py');

let mainWindow = null;
let tray = null;
let serverProcess = null;
let isQuitting = false;

// ─── Server Management ────────────────────────────────────────────────────────
function isServerReady() {
  return new Promise((resolve) => {
    const req = http.get(`${SERVER_URL}/health`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1500, () => { req.destroy(); resolve(false); });
  });
}

async function startServer() {
  const ready = await isServerReady();
  if (ready) {
    console.log('[Samir] Server already running.');
    return true;
  }

  console.log('[Samir] Starting Python backend (24/7 mode)...');
  const pyExe = fs.existsSync(VENV_PYTHON) ? VENV_PYTHON : 'python';

  serverProcess = spawn(pyExe, [RUN_SERVER], {
    cwd: CORE_DIR,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
  });
  if (serverProcess.unref) {
    serverProcess.unref();
  }

  serverProcess.on('exit', (code) => {
    console.log(`[Samir] Server process exited with code ${code}`);
  });

  // Wait up to 20s for server to be ready
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 500));
    if (await isServerReady()) {
      console.log('[Samir] Server is ready!');
      return true;
    }
  }
  console.error('[Samir] Server failed to start in time.');
  return false;
}

function stopServer() {
  if (serverProcess) {
    try {
      process.kill(serverProcess.pid);
    } catch (e) {}
    serverProcess = null;
  }
  // Also kill any lingering process on port 8000
  exec(`powershell -Command "Get-NetTCPConnection -LocalPort ${PORT} -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"`);
}

// ─── Window Management ────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    frame: false,           // نافذة مخصصة — JARVIS HUD titlebar
    transparent: false,     // غير شفافة لضمان السرعة الفائقة 60fps وعدم التعليق على ويندوز
    backgroundColor: '#000814',
    hasShadow: true,
    resizable: true,
    titleBarStyle: 'hidden',
    icon: ICON_PATH,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,   // للوصول للـ localhost API
    },
    show: false,            // نظهر عند الجاهزية مع timeout احتياطي
  });

  // تفعيل ومنح صلاحية الميكروفون والصوت تلقائياً لنافذة سمير
  session.defaultSession.setPermissionCheckHandler((webContents, permission) => {
    if (permission === 'media') return true;
    return false;
  });
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media') return callback(true);
    callback(false);
  });

  mainWindow.loadURL(SERVER_URL);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // صمام أمان لإظهار النافذة فوراً حتى لو تأخر حدث ready-to-show
  setTimeout(() => {
    if (mainWindow && !mainWindow.isVisible()) {
      mainWindow.show();
      mainWindow.focus();
    }
  }, 1200);

  // عند الضغط على X، نخفي في الـ tray بدلاً من الإغلاق
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      tray && tray.displayBalloon && tray.displayBalloon({
        title: 'سمير في الخلفية',
        content: 'سمير لا يزال يعمل في الخلفية. اضغط على الأيقونة لإظهاره.',
        iconType: 'info',
      });
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // DevTools in dev mode
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  return mainWindow;
}

function showWindow() {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
    if (mainWindow.isMinimized()) mainWindow.restore();
  } else {
    createWindow();
  }
}

// ─── System Tray ─────────────────────────────────────────────────────────────
function createTray() {
  let trayIcon;
  try {
    trayIcon = nativeImage.createFromPath(ICON_PATH);
    if (trayIcon.isEmpty()) throw new Error('empty');
    trayIcon = trayIcon.resize({ width: 16, height: 16 });
  } catch (e) {
    // أيقونة افتراضية مُولَّدة إذا ما لقينا الملف
    trayIcon = nativeImage.createEmpty();
  }

  tray = new Tray(trayIcon);
  tray.setToolTip('سمير — المساعد الذكي');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '🤖 فتح سمير',
      click: showWindow,
      bold: true,
    },
    { type: 'separator' },
    {
      label: '🔄 إعادة تشغيل الخادم',
      click: async () => {
        stopServer();
        await new Promise(r => setTimeout(r, 1000));
        await startServer();
        if (mainWindow) mainWindow.reload();
      },
    },
    {
      label: '📁 فتح مجلد سمير',
      click: () => shell.openPath(BASE_DIR),
    },
    { type: 'separator' },
    {
      label: '❌ إغلاق واجهة سمير (السيرفر يستمر 24/7)',
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
    {
      label: '⛔ إيقاف سمير والسيرفر نهائياً',
      click: () => {
        isQuitting = true;
        stopServer();
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);
  tray.on('double-click', showWindow);
  tray.on('click', showWindow);

  return tray;
}

// ─── IPC Handlers (للتواصل مع الـ window) ────────────────────────────────────
ipcMain.on('window-minimize', () => mainWindow && mainWindow.minimize());
ipcMain.on('window-maximize', () => {
  if (!mainWindow) return;
  mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize();
});
ipcMain.on('window-close', () => mainWindow && mainWindow.hide());
ipcMain.on('window-hide-tray', () => mainWindow && mainWindow.hide());
ipcMain.handle('is-maximized', () => mainWindow ? mainWindow.isMaximized() : false);

// ─── App Events ───────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  // منع تشغيل نسخ متعددة
  const lock = app.requestSingleInstanceLock();
  if (!lock) {
    app.quit();
    return;
  }

  app.on('second-instance', () => showWindow());

  // تشغيل الخادم أولاً
  const serverReady = await startServer();

  // إنشاء الـ tray أولاً (يشتغل حتى لو ما فتحنا النافذة)
  createTray();

  // إنشاء النافذة
  createWindow();

  if (!serverReady) {
    mainWindow.loadFile(path.join(__dirname, 'loading.html'));
    // إعادة المحاولة في الخلفية
    const retry = setInterval(async () => {
      if (await isServerReady()) {
        clearInterval(retry);
        mainWindow && mainWindow.loadURL(SERVER_URL);
      }
    }, 2000);
  }

  app.on('activate', showWindow);
});

app.on('window-all-closed', () => {
  // على Windows/Linux لا نغلق التطبيق عند إغلاق النوافذ — نبقى في الـ tray
  if (process.platform !== 'darwin') {
    // لا نفعل شيء — التطبيق يبقى في الـ system tray
  }
});

app.on('before-quit', () => {
  isQuitting = true;
});

app.on('will-quit', () => {
  // السيرفر يبقى شغال في الخلفية 24/7 دون انقطاع
  console.log('[Samir] Electron UI closed. Server continues running 24/7 in background.');
});
