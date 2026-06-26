import "@testing-library/jest-dom/vitest";

Object.defineProperty(window, "swai", {
  value: {
    getBackendInfo: async () => ({
      baseUrl: "http://127.0.0.1:8765",
      token: "dev-token",
      logsDir: ""
    }),
    onNavigateSettings: () => () => undefined,
    onExportMcpConfig: () => () => undefined
  },
  writable: true
});
