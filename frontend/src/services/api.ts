import type { ApiErrorShape } from "../types/api";

const LOCAL_DEV_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

function getBrowserHostname(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const host = window.location.hostname.trim();
  return host || null;
}

function isLocalDevHost(hostname: string): boolean {
  return LOCAL_DEV_HOSTS.has(hostname.toLowerCase());
}

function getDefaultProtocol(): string {
  if (typeof window !== "undefined" && /^https?:$/.test(window.location.protocol)) {
    return window.location.protocol;
  }
  return "http:";
}

function getDefaultApiBaseUrl(): string {
  const hostname = getBrowserHostname() || "127.0.0.1";
  return `${getDefaultProtocol()}//${hostname}:8000`;
}

function resolveApiBaseUrl(): string {
  const envValue = String(import.meta.env.VITE_API_BASE_URL || "").trim();
  if (!envValue) {
    return getDefaultApiBaseUrl();
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(envValue);
  } catch {
    throw new Error(
      "Invalid VITE_API_BASE_URL. Use full URL format (example: http://192.168.1.50:8000).",
    );
  }

  const browserHostname = getBrowserHostname();
  if (browserHostname && isLocalDevHost(parsedUrl.hostname) && !isLocalDevHost(browserHostname)) {
    parsedUrl.hostname = browserHostname;
  }

  return parsedUrl.toString();
}

const API_BASE_URL = resolveApiBaseUrl().replace(/\/+$/, "");

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type RequestOptions = {
  method?: HttpMethod;
  body?: BodyInit | object;
  token?: string | null;
  headers?: Record<string, string>;
};

type UnauthorizedHandler = (() => void) | null;

let unauthorizedHandler: UnauthorizedHandler = null;

export function registerUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

function normalizePath(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  if (path.startsWith("/")) {
    return `${API_BASE_URL}${path}`;
  }

  return `${API_BASE_URL}/${path}`;
}

function toBody(body: RequestOptions["body"], headers: Record<string, string>): BodyInit | undefined {
  if (!body) {
    return undefined;
  }

  if (body instanceof FormData) {
    return body;
  }

  if (typeof body === "string" || body instanceof Blob || body instanceof URLSearchParams) {
    return body;
  }

  headers["Content-Type"] = "application/json";
  return JSON.stringify(body);
}

async function parseError(response: Response): Promise<string> {
  const fallback = `${response.status} ${response.statusText}`;

  try {
    const data = (await response.json()) as ApiErrorShape;
    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
    if (typeof data.message === "string" && data.message.trim()) {
      return data.message;
    }
    return fallback;
  } catch {
    return fallback;
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers || {}) };

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  const response = await fetch(normalizePath(path), {
    method: options.method || "GET",
    headers,
    body: toBody(options.body, headers),
  });

  if (!response.ok) {
    if (response.status === 401 && unauthorizedHandler) {
      unauthorizedHandler();
    }
    throw new Error(await parseError(response));
  }

  return (await response.json()) as T;
}

export async function fetchBinary(path: string, token?: string | null): Promise<Blob> {
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(normalizePath(path), { method: "GET", headers });
  if (!response.ok) {
    if (response.status === 401 && unauthorizedHandler) {
      unauthorizedHandler();
    }
    throw new Error(await parseError(response));
  }

  return response.blob();
}

export function resolveApiPath(path: string): string {
  return normalizePath(path);
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}
