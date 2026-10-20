const { contextBridge, ipcRenderer } = require('electron');

// تعريض API آمن للـ window
contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
  hideToTray: () => ipcRenderer.send('window-hide-tray'),
  isMaximized: () => ipcRenderer.invoke('is-maximized'),
  platform: process.platform,
});
