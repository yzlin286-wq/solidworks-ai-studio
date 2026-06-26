/// <reference types="vite/client" />

interface BackendInfo {
  baseUrl: string;
  token: string;
  logsDir: string;
}

interface SolidWorksAIStudioBridge {
  getBackendInfo: () => Promise<BackendInfo>;
  onNavigateSettings: (callback: () => void) => () => void;
  onExportMcpConfig: (callback: () => void) => () => void;
}

interface Window {
  swai?: SolidWorksAIStudioBridge;
}
