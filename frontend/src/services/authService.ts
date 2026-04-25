import type { AuthTokenResponse, AuthUser } from "../types/auth";

import { apiRequest } from "./api";

export function login(identifier: string, password: string): Promise<AuthTokenResponse> {
  return apiRequest<AuthTokenResponse>("/auth/login", {
    method: "POST",
    body: { identifier, password },
  });
}

export function register(params: {
  username: string;
  email: string;
  password: string;
  display_name?: string;
}): Promise<AuthTokenResponse> {
  return apiRequest<AuthTokenResponse>("/auth/register", {
    method: "POST",
    body: params,
  });
}

export function me(token: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me", {
    token,
  });
}
