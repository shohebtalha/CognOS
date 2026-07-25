export {};

declare global {
  interface Window {
    cognos?: {
      apiBase: string;
      backendStatus: () => Promise<{
        running: boolean;
        pid: number | null;
        lastError: string | null;
        mode: string;
      }>;
      toggleOverlay: () => Promise<boolean>;
    };
  }
}
