import { create } from "zustand";

import type { AuthUser } from "../types/auth";

export type { AuthUser };

type StoredAuthPayload = {
  token: string;
  user: AuthUser;
  expiresAt: number;
};

type AuthState = {
  token: string | null;
  user: AuthUser | null;
  expiresAt: number;
  setAuth: (token: string, user: AuthUser, expiresInSeconds: number) => void;
  clearAuth: () => void;
  isTokenExpired: () => boolean;
};

const AUTH_STORAGE_KEY = "boran_auth_v2";

function readStoredAuth(): Pick<AuthState, "token" | "user" | "expiresAt"> {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) {
      return { token: null, user: null, expiresAt: 0 };
    }

    const parsed = JSON.parse(raw) as StoredAuthPayload;
    if (!parsed.token || !parsed.user || !parsed.expiresAt) {
      return { token: null, user: null, expiresAt: 0 };
    }

    return {
      token: parsed.token,
      user: parsed.user,
      expiresAt: parsed.expiresAt,
    };
  } catch {
    return { token: null, user: null, expiresAt: 0 };
  }
}

function persistAuth(payload: StoredAuthPayload): void {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(payload));
}

function clearStoredAuth(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

export const useAuthStore = create<AuthState>((set, get) => ({
  ...readStoredAuth(),
  setAuth: (token, user, expiresInSeconds) => {
    const expiresAt = Date.now() + Math.max(1, expiresInSeconds) * 1000;
    const payload: StoredAuthPayload = { token, user, expiresAt };
    persistAuth(payload);
    set(payload);
  },
  clearAuth: () => {
    clearStoredAuth();
    set({ token: null, user: null, expiresAt: 0 });
  },
  isTokenExpired: () => {
    const { token, expiresAt } = get();
    if (!token || !expiresAt) {
      return true;
    }
    return Date.now() >= expiresAt;
  },
}));
