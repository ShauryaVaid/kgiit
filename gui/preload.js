const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // Simple pass-through or constants could go here if needed
});
