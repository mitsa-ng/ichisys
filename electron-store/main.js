const { app, BrowserWindow, Menu, shell, dialog, ipcMain } = require('electron')
const path = require('path')
const fs = require('fs')

let mainWindow = null

function getConfigPath() {
  const base = app.getPath('userData')
  return path.join(base, 'config.json')
}

function loadConfig() {
  try {
    const raw = fs.readFileSync(getConfigPath(), 'utf-8')
    return JSON.parse(raw)
  } catch {
    return { serverUrl: '' }
  }
}

function saveConfig(config) {
  const dir = path.dirname(getConfigPath())
  fs.mkdirSync(dir, { recursive: true })
  fs.writeFileSync(getConfigPath(), JSON.stringify(config, null, 2), 'utf-8')
}

async function promptForUrl() {
  const config = loadConfig()
  const { response } = await dialog.showMessageBox(mainWindow, {
    type: 'question',
    title: '設定伺服器',
    message: '請輸入後端伺服器網址',
    detail: '範例：http://192.168.1.100:8000',
    buttons: ['確定', '離開'],
  })
  if (response === 1) return null

  const { value } = await mainWindow.webContents.executeJavaScript(
    `window.prompt('請輸入後端伺服器網址（含 http://）：', '${config.serverUrl || 'http://'}')`
  )
  if (!value || !value.trim()) return null

  const url = value.trim().replace(/\/+$/, '')
  saveConfig({ serverUrl: url })
  return url
}

function navigateTo(url) {
  if (!url) return
  mainWindow?.loadURL(url)
}

async function ensureServerUrl() {
  const config = loadConfig()
  if (config.serverUrl) {
    return config.serverUrl
  }
  return await promptForUrl()
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
    title: '一番賞抽獎系統 - 店面端',
    kiosk: false,
    fullscreen: false,
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

async function initialize() {
  createWindow()
  const url = await ensureServerUrl()
  if (url) {
    navigateTo(url)
  } else {
    app.quit()
  }
}

function buildMenu() {
  const template = [
    {
      label: '系統',
      submenu: [
        {
          label: '重新設定伺服器網址',
          accelerator: 'F12',
          click: async () => {
            const url = await promptForUrl()
            if (url) navigateTo(url)
          },
        },
        {
          label: '重新整理',
          accelerator: 'CmdOrCtrl+R',
          click: () => mainWindow?.reload(),
        },
        { type: 'separator' },
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
        { type: 'separator' },
        { role: 'quit', label: '結束' },
      ],
    },
    {
      label: '說明',
      submenu: [
        {
          label: '關於一番賞抽獎系統',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: '關於一番賞抽獎系統',
              message: '一番賞抽獎系統 - 店面端',
              detail: '版本 1.0.0\n\n連線至後端伺服器進行抽獎。\n設定 → 重新設定伺服器網址 可更改連線目標。',
            })
          },
        },
      ],
    },
  ]
  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

app.whenReady().then(() => {
  buildMenu()
  initialize()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      initialize()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
