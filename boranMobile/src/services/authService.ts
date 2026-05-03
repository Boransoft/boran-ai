import { apiClient } from "./api";
import { AuthTokenResponse } from "../utils/types";
import { clearAuthToken, getAuthToken } from "../utils/storage";

type LoginParams = {
  email: string;
  password: string;
};

type RegisterParams = {
  username: string;
  email: string;
  password: string;
  displayName: string;
};

export async function login(params: LoginParams): Promise<AuthTokenResponse> {
  const { data } = await apiClient.post<AuthTokenResponse>("/auth/login", {
    identifier: params.email,
    password: params.password,
  });
  return normalizeAuthTokenResponse(data);
}

export async function register(params: RegisterParams): Promise<AuthTokenResponse> {
  const { data } = await apiClient.post<AuthTokenResponse>("/auth/register", {
    username: params.username,
    email: params.email,
    password: params.password,
    display_name: params.displayName,
  });
  return normalizeAuthTokenResponse(data);
}

function normalizeAuthTokenResponse(data: AuthTokenResponse): AuthTokenResponse {
  const token = typeof data.access_token === "string" ? data.access_token.trim() : "";
  console.log("[auth-service] login/register token:", {
    hasToken: Boolean(token),
    tokenPrefix: token.slice(0, 12),
  });
  if (!token) {
    throw new Error("Auth response icinde access_token bos geldi.");
  }
  return {
    ...data,
    access_token: token,
  };
}

type JwtPayload = {
  exp?: number;
};

function decodeJwtPayload(token: string): JwtPayload | null {
  const parts = token.split(".");
  if (parts.length < 2) {
    return null;
  }

  const decodeBase64 = (globalThis as { atob?: (value: string) => string }).atob;
  if (typeof decodeBase64 !== "function") {
    return null;
  }

  try {
    const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const decoded = decodeBase64(padded);
    return JSON.parse(decoded) as JwtPayload;
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") {
    return false;
  }
  return payload.exp * 1000 <= Date.now();
}

export async function getStoredValidToken(): Promise<string | null> {
  const storedToken = await getAuthToken();
  if (!storedToken) {
    return null;
  }

  if (isTokenExpired(storedToken)) {
    await clearAuthToken();
    return null;
  }

  return storedToken;
}
