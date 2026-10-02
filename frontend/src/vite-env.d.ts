/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Base URL of the FastAPI service.
   * - Local dev: unset (Vite proxies /api to 127.0.0.1:8000)
   * - Production: e.g. https://mlcshop.onrender.com/api
   */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
