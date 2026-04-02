import { apiRequest } from "./api";

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    external_id: string;
    username?: string | null;
    email?: string | null;
    display_name?: string | null;
  };
};

export function login(identifier: string, password: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: { identifier, password },
  });
}

export function register(params: {
  username: string;
  email: string;
  password: string;
  display_name?: string;
}): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/register", {
    method: "POST",
    body: params,
  });
}

export function me(token: string) {
  return apiRequest<TokenResponse["user"]>("/auth/me", {
    token,
  });
}
