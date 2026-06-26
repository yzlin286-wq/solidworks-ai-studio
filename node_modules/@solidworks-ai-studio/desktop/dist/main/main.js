import { app, BrowserWindow, Menu, ipcMain, shell } from "electron";
import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
let mainWindow = null;
let backendProcess = null;
let backendInfo = {
    baseUrl: process.env.SWAI_API_URL ?? "http://127.0.0.1:8765",
    token: process.env.SWAI_API_TOKEN ?? "dev-token",
    logsDir: path.join(app.getPath("userData"), "logs")
};
function outputDir() {
    return process.env.SWAI_OUTPUT_DIR ?? path.join(app.getPath("userData"), "outputs");
}
async function findFreePort() {
    return await new Promise((resolve, reject) => {
        const server = net.createServer();
        server.once("error", reject);
        server.listen(0, "127.0.0.1", () => {
            const address = server.address();
            if (typeof address === "object" && address) {
                const port = address.port;
                server.close(() => resolve(port));
            }
            else {
                server.close(() => reject(new Error("Could not allocate a local backend port.")));
            }
        });
    });
}
async function startBackend() {
    fs.mkdirSync(backendInfo.logsDir, { recursive: true });
    if (!app.isPackaged) {
        backendInfo = {
            baseUrl: process.env.SWAI_API_URL ?? "http://127.0.0.1:8765",
            token: process.env.SWAI_API_TOKEN ?? "dev-token",
            logsDir: path.join(app.getPath("userData"), "logs")
        };
        return;
    }
    const port = await findFreePort();
    const token = crypto.randomUUID();
    const executable = path.join(process.resourcesPath, "backend", "sw-ai-backend.exe");
    backendInfo = {
        baseUrl: `http://127.0.0.1:${port}`,
        token,
        logsDir: path.join(app.getPath("userData"), "logs")
    };
    backendProcess = spawn(executable, [], {
        env: {
            ...process.env,
            SWAI_API_PORT: String(port),
            SWAI_API_TOKEN: token,
            SWAI_USER_DATA_DIR: app.getPath("userData"),
            SWAI_OUTPUT_DIR: outputDir()
        },
        windowsHide: true
    });
    const logFile = fs.createWriteStream(path.join(backendInfo.logsDir, "backend.log"), { flags: "a" });
    backendProcess.stdout.pipe(logFile);
    backendProcess.stderr.pipe(logFile);
}
function stopBackend() {
    if (backendProcess && !backendProcess.killed) {
        backendProcess.kill();
    }
    backendProcess = null;
}
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1480,
        height: 940,
        minWidth: 1120,
        minHeight: 760,
        title: "SolidWorks AI Studio",
        backgroundColor: "#0d1214",
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
            preload: path.join(__dirname, "../preload/preload.cjs")
        }
    });
    if (!app.isPackaged) {
        void mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL ?? "http://127.0.0.1:5173");
    }
    else {
        void mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
    }
}
function buildMenu() {
    const template = [
        {
            label: "File",
            submenu: [
                {
                    label: "Settings",
                    accelerator: "CmdOrCtrl+,",
                    click: () => mainWindow?.webContents.send("navigate-settings")
                },
                {
                    label: "Open Logs",
                    click: () => {
                        fs.mkdirSync(backendInfo.logsDir, { recursive: true });
                        void shell.openPath(backendInfo.logsDir);
                    }
                },
                {
                    label: "Export MCP Config",
                    click: () => mainWindow?.webContents.send("export-mcp-config")
                },
                { type: "separator" },
                { role: "quit" }
            ]
        },
        {
            label: "Backend",
            submenu: [
                {
                    label: "Restart Backend",
                    click: async () => {
                        stopBackend();
                        await startBackend();
                    }
                }
            ]
        },
        {
            label: "Help",
            submenu: [
                {
                    label: "About",
                    click: () => {
                        void shell.openExternal("https://github.com/wzyn20051216/solidworks-automation-skill");
                    }
                }
            ]
        }
    ];
    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}
ipcMain.handle("swai:get-backend-info", () => backendInfo);
app.whenReady().then(async () => {
    await startBackend();
    buildMenu();
    createWindow();
});
app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        app.quit();
    }
});
app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});
app.on("before-quit", () => {
    stopBackend();
});
