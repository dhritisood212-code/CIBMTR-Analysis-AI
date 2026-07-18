// Reads the runtime config injected by public/config.js (see index.html). Editing config.js
// on the deployed site changes the backend URL without a rebuild.
declare global {
  interface Window {
    __APP_CONFIG__?: { apiBase?: string };
  }
}

export const API_BASE: string =
  (typeof window !== "undefined" && window.__APP_CONFIG__?.apiBase) || "";

export {};
