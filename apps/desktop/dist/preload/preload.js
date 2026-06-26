import { contextBridge, ipcRenderer } from "electron";
contextBridge.exposeInMainWorld("swai", {
    getBackendInfo: async () => ipcRenderer.invoke("swai:get-backend-info"),
    onNavigateSettings: (callback) => {
        ipcRenderer.on("navigate-settings", callback);
        return () => ipcRenderer.removeListener("navigate-settings", callback);
    },
    onExportMcpConfig: (callback) => {
        ipcRenderer.on("export-mcp-config", callback);
        return () => ipcRenderer.removeListener("export-mcp-config", callback);
    }
});
