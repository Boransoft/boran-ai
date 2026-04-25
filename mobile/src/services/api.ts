import axios from "axios";

import { getApiBaseUrl } from "../utils/env";

export const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 60000,
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
  const base = getApiBaseUrl().replace(/\/+$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalized}`;
}

export function toFileUri(path: string): string {
  if (path.startsWith("file://") || path.startsWith("content://") || path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `file://${path}`;
}
