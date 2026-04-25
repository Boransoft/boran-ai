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
  activeApiBaseUrl = resolved;
  apiClient.defaults.baseURL = resolved;
  return resolved;
}

export async function setActiveApiBaseUrl(baseUrl: string): Promise<string> {
  const saved = await saveApiBaseUrl(baseUrl);
  activeApiBaseUrl = saved;
  apiClient.defaults.baseURL = saved;
  return saved;
}

apiClient.interceptors.request.use((config) => {
  config.baseURL = activeApiBaseUrl;
  return config;
});

export function authHeader(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
  };
}

export function toAbsoluteApiUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const base = activeApiBaseUrl.replace(/\/+$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalized}`;
}

export function toFileUri(path: string): string {
  if (path.startsWith("file://") || path.startsWith("content://") || path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `file://${path}`;
}
