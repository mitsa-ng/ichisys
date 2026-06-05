const { app, BrowserWindow, Menu, shell, dialog } = require('electron')
const path = require('path')

const DEFAULT_URL = 'https://ichisys.vercel.app'
let mainWindow = null

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
  })

  mainWindow.loadURL(DEFAULT_URL)

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
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
          click: () => mainWindow?.loadURL(DEFAULT_URL),
        },
        {
          label: '管理後台',
          click: () => mainWindow?.loadURL(`${DEFAULT_URL}/admin/login`),
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

app.whenReady().then(() => {
  buildMenu()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
