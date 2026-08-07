const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  getTrackId: () => process.env.TRACK_ID || 'git-basics',
  getAuthToken: () => process.env.KGIIT_AUTH_TOKEN || '',
  selectDirectory: () => ipcRenderer.invoke('dialog:selectDirectory')
});
