import { apiClient } from "./api";
import { AuthTokenResponse } from "../utils/types";

type LoginParams = {
  email: string;
  password: string;
};

export async function login(params: LoginParams): Promise<AuthTokenResponse> {
  const { data } = await apiClient.post<AuthTokenResponse>("/auth/login", {
    identifier: params.email,
    password: params.password,
  });
  return data;
}
