const { app, BrowserWindow, Menu, shell, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const http = require('http')

const BACKEND_PORT = 8000
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`
let mainWindow = null
let backendProcess = null

function getBackendPath() {
  const isDev = !app.isPackaged
  if (isDev) {
    return {
      command: 'uvicorn',
      args: ['app.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT), '--log-level', 'info'],
      cwd: path.join(__dirname, '..', 'backend'),
    }
  }
  // Packaged: backend is in the extraResources/backend folder
  const resourcePath = process.resourcesPath
  const ext = process.platform === 'win32' ? '.exe' : ''
  return {
    command: path.join(resourcePath, 'backend', 'ichiban-server' + ext),
    args: [],
    cwd: path.join(resourcePath, 'backend'),
  }
}

function startBackend() {
  return new Promise((resolve, reject) => {
    const { command, args, cwd } = getBackendPath()
    console.log(`Starting backend: ${command} ${args.join(' ')}`)

    backendProcess = spawn(command, args, {
      cwd,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, PORT: String(BACKEND_PORT), HOST: '127.0.0.1' },
    })

    backendProcess.stdout.on('data', (data) => {
      const text = data.toString()
      console.log('[backend]', text)
      if (text.includes('Uvicorn running')) {
        resolve()
      }
    })

    backendProcess.stderr.on('data', (data) => {
      const text = data.toString()
      console.log('[backend]', text)
      // Uvicorn logs to stderr
      if (text.includes('Uvicorn running')) {
        resolve()
      }
    })

    backendProcess.on('error', (err) => {
      console.error('Failed to start backend:', err)
      reject(err)
    })

    backendProcess.on('exit', (code) => {
      console.log('Backend exited with code:', code)
      backendProcess = null
    })

    // Timeout fallback — try connecting
    setTimeout(() => {
      waitForBackend(resolve, reject, 0)
    }, 3000)
  })
}

function waitForBackend(resolve, reject, attempt) {
  if (attempt > 20) {
    reject(new Error('Backend did not start in time'))
    return
  }
  http.get(`${BACKEND_URL}/api/health`, (res) => {
    if (res.statusCode === 200) {
      resolve()
    } else {
      setTimeout(() => waitForBackend(resolve, reject, attempt + 1), 1000)
    }
  }).on('error', () => {
    setTimeout(() => waitForBackend(resolve, reject, attempt + 1), 1000)
  })
}

function stopBackend() {
  if (backendProcess) {
    console.log('Stopping backend...')
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(backendProcess.pid), '/f', '/t'])
    } else {
      backendProcess.kill('SIGTERM')
    }
    backendProcess = null
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    minWidth: 900,
    minHeight: 700,
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    autoHideMenuBar: true,
    title: '一番賞抽獎系統',
  })

  mainWindow.loadURL(BACKEND_URL)

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function buildMenu() {
  const template = [
    {
      label: '一番賞系統',
      submenu: [
        {
          label: '重新載入',
          accelerator: 'CmdOrCtrl+R',
          click: () => mainWindow?.reload(),
        },
        { type: 'separator' },
        {
          label: '開發者工具',
          accelerator: 'CmdOrCtrl+Shift+I',
          click: () => mainWindow?.webContents.toggleDevTools(),
        },
        { type: 'separator' },
        { role: 'quit', label: '結束' },
      ],
    },
    {
      label: '前往',
      submenu: [
        {
          label: '前台首頁',
          click: () => mainWindow?.loadURL(BACKEND_URL),
        },
        {
          label: '管理後台',
          click: () => mainWindow?.loadURL(`${BACKEND_URL}/admin/login`),
        },
        {
          label: '輸入網址...',
          accelerator: 'CmdOrCtrl+L',
          click: () => {
            mainWindow?.webContents.executeJavaScript(
              'window.prompt("請輸入網址：", "' + mainWindow?.getURL() + '")'
            ).then(url => {
              if (url && url.trim()) {
                mainWindow?.loadURL(url.trim())
              }
            })
          },
        },
      ],
    },
    {
      label: '顯示',
      submenu: [
        {
          label: '全螢幕',
          accelerator: 'F11',
          click: () => {
            if (mainWindow?.isFullScreen()) {
              mainWindow?.setFullScreen(false)
            } else {
              mainWindow?.setFullScreen(true)
            }
          },
        },
        {
          label: '離開全螢幕',
          accelerator: 'Esc',
          click: () => mainWindow?.setFullScreen(false),
        },
        { type: 'separator' },
        { role: 'togglefullscreen', label: '切換全螢幕' },
      ],
    },
    {
      label: '說明',
      submenu: [
        {
          label: '關於一番賞系統',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: '關於一番賞系統',
              message: '一番賞抽獎系統 - 店面端',
              detail: '版本 1.0.0\n\n一番賞 O2O 抽獎管理系統\n讓顧客在店內直接抽獎，自動連線後台管理。',
            })
          },
        },
      ],
    },
  ]

  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

app.whenReady().then(async () => {
  buildMenu()
  try {
    await startBackend()
    console.log('Backend is ready')
    createWindow()
  } catch (err) {
    console.error('Failed to start backend:', err)
    dialog.showErrorBox('啟動失敗', '無法啟動後端伺服器，請確認 ichiban-server 執行檔存在。')
    app.quit()
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  stopBackend()
})
