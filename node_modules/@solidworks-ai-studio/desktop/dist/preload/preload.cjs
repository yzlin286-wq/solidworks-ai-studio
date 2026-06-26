"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld("swai", {
    getBackendInfo: async () => electron_1.ipcRenderer.invoke("swai:get-backend-info"),
    onNavigateSettings: (callback) => {
        electron_1.ipcRenderer.on("navigate-settings", callback);
        return () => electron_1.ipcRenderer.removeListener("navigate-settings", callback);
    },
    onExportMcpConfig: (callback) => {
        electron_1.ipcRenderer.on("export-mcp-config", callback);
        return () => electron_1.ipcRenderer.removeListener("export-mcp-config", callback);
    }
});
