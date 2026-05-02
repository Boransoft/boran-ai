import { apiClient } from "./api";
import { AuthTokenResponse } from "../utils/types";

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
  return data;
}

export async function register(params: RegisterParams): Promise<AuthTokenResponse> {
  const { data } = await apiClient.post<AuthTokenResponse>("/auth/register", {
    username: params.username,
    email: params.email,
    password: params.password,
    display_name: params.displayName,
  });
  return data;
}

// Mobile app network error message improvements:
// 1. "Sunucuya ulaşılamadı" -> "Sunu
