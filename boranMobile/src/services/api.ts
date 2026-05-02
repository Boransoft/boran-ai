import axios from "axios";

import { getApiBaseUrl, resolveApiBaseUrl, saveApiBaseUrl } from "../utils/env";

export const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 60000,
});

let activeApiBaseUrl = apiClient.defaults.baseURL ?? getApiBaseUrl();

export function getActiveApiBaseUrl(): string {
  return activeApiBaseUrl;
}

export async function syncApiBaseUrlFromStorage(): Promise<string> {
  const resolved = await resolveApiBaseUrl();
  await setActiveApiBaseUrl(resolved);
  return resolved;
}

export async function setActiveApiBaseUrl(url: string): Promise<string> {
  const normalized = normalizeApiBaseUrl(url);
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