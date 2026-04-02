import { create } from "zustand";

export type AuthUser = {
  id: string;
  external_id: string;
  username?: string | null;
  email?: string | null;
  display_name?: string | null;
};

type AuthState = {
  token: string | null;
  user: AuthUser | null;
  expiresIn: number;
  setAuth: (token: string, user: AuthUser, expiresIn: number) => void;
  clearAuth: () => void;
};

const AUTH_STORAGE_KEY = "boran_auth";

function loadInitialState(): Pick<AuthState, "token" | "user" | "expiresIn"> {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return { token: null, user: null, expiresIn: 0 };
    const parsed = JSON.parse(raw) as {
      token: string;
      user: AuthUser;
      expiresIn: number;
    };
    return {
      token: parsed.token,
      user: parsed.user,
      expiresIn: parsed.expiresIn,
    };
  } catch {
    return { token: null, user: null, expiresIn: 0 };
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  ...loadInitialState(),
  setAuth: (token, user, expiresIn) => {
    const payload = { token, user, expiresIn };
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(payload));
    set(payload);
  },
  clearAuth: () => {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    set({ token: null, user: null, expiresIn: 0 });
  },
}));
