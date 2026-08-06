const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('api', {
  getTrackId: () => process.env.TRACK_ID || 'git-basics'
});
