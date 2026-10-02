/**
 * API base URL.
 *
 * - Local dev: VITE_API_URL is unset → requests go to `/api`, which the Vite
 *   dev server proxies to http://127.0.0.1:8000.
 * - Production: VITE_API_URL is set (e.g. `https://mlcshop.onrender.com/api`),
 *   so the SPA talks to the deployed FastAPI service on Render.
 */
const API_BASE = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/+$/, '');

// Guard against shipping a production build without the API URL configured —
// without it the SPA would call /api on its own (Vercel) domain and fail.
if (import.meta.env.PROD && !import.meta.env.VITE_API_URL) {
  console.warn(
    '[mlc] VITE_API_URL is not set for this build — API requests will go to /api on this domain.',
  );
}

/** Build a full URL for an API path such as `/auth/google/redirect`. */
export function apiUrl(path: string): string {
  return API_BASE + (path.startsWith('/') ? path : `/${path}`);
}

const TOKEN_KEY = 'mlc_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  errors: Record<string, string[]>;

  constructor(message: string, status: number, errors: Record<string, string[]> = {}) {
    super(message);
    this.status = status;
    this.errors = errors;
  }

  /** First validation message for a field, if any. */
  field(name: string): string | undefined {
    return this.errors[name]?.[0];
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getToken();

  const response = await fetch(apiUrl(path), {
    method: options.method ?? 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  const text = await response.text();
  const json = text ? JSON.parse(text) : {};

  if (!response.ok) {
    throw new ApiError(
      json.message ?? `Request failed (${response.status})`,
      response.status,
      json.errors ?? {},
    );
  }

  return json as T;
}
