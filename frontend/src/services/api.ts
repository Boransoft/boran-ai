import type { ApiErrorShape } from "../types/api";

const DEFAULT_API_BASE_URL = "https://boran-ai.onrender.com";

function resolveApiBaseUrl(): string {
  const resolvedValue = String(import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).trim();

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(resolvedValue);
  } catch {
    throw new Error(
      "Invalid VITE_API_BASE_URL. Use full URL format (example: https://boran-ai.onrender.com).",
    );
  }

  const resolvedUrl = parsedUrl.toString();
  console.info("[api] using API base URL:", resolvedUrl);
  return resolvedUrl;
}

const API_BASE_URL = resolveApiBaseUrl().replace(/\/+$/, "");

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type RequestOptions = {
  method?: HttpMethod;
  body?: BodyInit | object;
  token?: string | null;
  headers?: Record<string, string>;
  timeoutMs?: number;
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
    const data = (await response.clone().json()) as ApiErrorShape;
    console.error("[api] backend error response", {
      status: response.status,
      statusText: response.statusText,
      body: data,
    });
    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      return data.detail
        .map((item) => {
          if (typeof item === "string") {
            return item;
          }
          if (item && typeof item === "object") {
            const record = item as Record<string, unknown>;
            const message = typeof record.msg === "string" ? record.msg : JSON.stringify(record);
            const location = Array.isArray(record.loc) ? record.loc.join(".") : "";
            return location ? `${location}: ${message}` : message;
          }
          return String(item);
        })
        .join("; ");
    }
    if (typeof data.message === "string" && data.message.trim()) {
      return data.message;
    }
    return fallback;
  } catch (jsonError) {
    try {
      const text = await response.text();
      if (text.trim()) {
        console.error("[api] non-json backend error response", {
          status: response.status,
          statusText: response.statusText,
          body: text,
        });
        return `${fallback}: ${text.trim().slice(0, 600)}`;
      }
    } catch {
      console.error("[api] failed to read backend error body", jsonError);
    }
    return fallback;
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers || {}) };

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  const requestUrl = normalizePath(path);
  const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
  const timeoutMs = options.timeoutMs && options.timeoutMs > 0 ? options.timeoutMs : 0;
  const timeoutId =
    controller && timeoutMs > 0
      ? window.setTimeout(() => {
          controller.abort();
        }, timeoutMs)
      : null;
  let response: Response;
  try {
    response = await fetch(requestUrl, {
      method: options.method || "GET",
      headers,
      body: toBody(options.body, headers),
      signal: controller?.signal,
    });
  } catch (error) {
    const isAbort = error instanceof DOMException && error.name === "AbortError";
    const detail = isAbort
      ? `AI yaniti zaman asimina ugradi (${Math.round(timeoutMs / 1000)} sn). Model su anda yanit vermiyor.`
      : error instanceof Error && error.message
        ? error.message
        : "Network request failed.";
    console.error("[api] network/CORS request failed", {
      apiBaseUrl: API_BASE_URL,
      requestUrl,
      error,
    });
    if (isAbort) {
      throw new Error(detail);
    }
    throw new Error(
      `Backend'e ulasilamadi. API: ${API_BASE_URL}. URL: ${requestUrl}. Detay: ${detail}`,
    );
  } finally {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
  }

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
