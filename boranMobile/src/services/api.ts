import axios from "axios";

import { getApiBaseUrl, resolveApiBaseUrl, saveApiBaseUrl } from "../utils/env";

const DEFAULT_API_BASE_URL = "https://boran-ai.onrender.com";

export const apiClient = axios.create({
  baseURL: DEFAULT_API_BASE_URL,
  timeout: 60000,
});

let activeApiBaseUrl = apiClient.defaults.baseURL ?? DEFAULT_API_BASE_URL;
let authFailureHandler: (() => void | Promise<void>) | null = null;
let isHandlingAuthFailure = false;

function sanitizeApiBaseUrl(url: string): string {
  const normalized = normalizeApiBaseUrl(url);
  if (!normalized) {
    return DEFAULT_API_BASE_URL;
  }
  if (/^https?:\/\/(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?$/i.test(normalized)) {
    return DEFAULT_API_BASE_URL;
  }
  return normalized;
}

function extractErrorText(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map((item) => extractErrorText(item)).filter(Boolean).join(" ");
  }

  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return [record.detail, record.message, record.error]
      .map((item) => extractErrorText(item))
      .filter(Boolean)
      .join(" ");
  }

  return "";
}

function shouldForceLogout(error: unknown): boolean {
  const response = axios.isAxiosError(error) ? error.response : undefined;
  const status = response?.status;
  if (status === 401) {
    return true;
  }

  const detailText = extractErrorText(response?.data).toLowerCase();
  return detailText.includes("token expired");
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (shouldForceLogout(error) && authFailureHandler && !isHandlingAuthFailure) {
      isHandlingAuthFailure = true;
      try {
        await authFailureHandler();
      } finally {
        isHandlingAuthFailure = false;
      }
    }
    return Promise.reject(error);
  },
);

export function getActiveApiBaseUrl(): string {
  return activeApiBaseUrl;
}

export function setAuthFailureHandler(handler: (() => void | Promise<void>) | null): void {
  authFailureHandler = handler;
}

export async function triggerAuthFailure(): Promise<void> {
  if (authFailureHandler) {
    await authFailureHandler();
  }
}

export async function syncApiBaseUrlFromStorage(): Promise<string> {
  const resolved = await resolveApiBaseUrl();
  const sanitized = sanitizeApiBaseUrl(resolved);
  await setActiveApiBaseUrl(sanitized);
  if (sanitized !== resolved) {
    await saveApiBaseUrl(sanitized);
  }
  return sanitized;
}

export async function setActiveApiBaseUrl(url: string): Promise<string> {
  const normalized = sanitizeApiBaseUrl(url);
  await saveApiBaseUrl(normalized);
  apiClient.defaults.baseURL = normalized;
  activeApiBaseUrl = normalized;
  return normalized;
}

export function authHeader(token: string): { Authorization: string } {
  return {
    Authorization: `Bearer ${token}`,
  };
}

export function toAbsoluteApiUrl(path: string): string {
  const base = getActiveApiBaseUrl().replace(/\/+$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

export function normalizeApiBaseUrl(url: string): string {
  const cleaned = url.trim().replace(/\/+$/, "");

  if (!cleaned) {
    return getApiBaseUrl();
  }

  if (!cleaned.startsWith("http://") && !cleaned.startsWith("https://")) {
    return `https://${cleaned}`;
  }

  return cleaned;
}

export function toFileUri(uri: string): string {
  if (uri.startsWith("file://")) {
    return uri;
  }

  return `file://${uri}`;
}
