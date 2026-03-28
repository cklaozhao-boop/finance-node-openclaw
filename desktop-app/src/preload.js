const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("financeDesktop", {
  bootstrap: () => ipcRenderer.invoke("desktop:bootstrap"),
  refresh: () => ipcRenderer.invoke("desktop:refresh"),
  bindAgent: (agentName) => ipcRenderer.invoke("desktop:bind-agent", agentName),
  openExternal: (url) => ipcRenderer.invoke("desktop:open-external", url),
  onBootstrapLog: (handler) => {
    const listener = (_event, message) => handler(message);
    ipcRenderer.on("bootstrap-log", listener);
    return () => ipcRenderer.removeListener("bootstrap-log", listener);
  }
});
