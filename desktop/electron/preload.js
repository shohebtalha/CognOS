const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("cognos", {
  apiBase: "http://127.0.0.1:8420",
  backendStatus: () => ipcRenderer.invoke("backend-status"),
  toggleOverlay: () => ipcRenderer.invoke("toggle-overlay")
});
