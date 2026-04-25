import { useCallback, useEffect } from "react";

import AdminPage from "./pages/AdminPage";
import AuthPage from "./pages/AuthPage";
import MainAppPage from "./pages/MainAppPage";
import { registerUnauthorizedHandler } from "./services/api";
import { useAppStore } from "./store/appStore";
import { useAuthStore } from "./store/authStore";
import { useMessageStore } from "./store/messageStore";
import {
  CLEAR_PERSISTED_MESSAGES_ON_LOGOUT_DEFAULT,
  clearSessionCacheForUser,
} from "./store/persistence";
import { useUploadStore } from "./store/uploadStore";

export default function App() {
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const isTokenExpired = useAuthStore((state) => state.isTokenExpired);
  const setSystemState = useAppStore((state) => state.setSystemState);
  const clearActiveUserUploadCache = useUploadStore((state) => state.clearActiveUserCache);
  const clearActiveUserMessageCache = useMessageStore((state) => state.clearActiveUserCache);

  const currentUserExternalId = user?.external_id || null;

  const runLogoutCleanup = useCallback(() => {
    clearSessionCacheForUser(currentUserExternalId);
    clearActiveUserUploadCache();
    clearActiveUserMessageCache({
      clearPersisted: CLEAR_PERSISTED_MESSAGES_ON_LOGOUT_DEFAULT,
    });
    clearAuth();
  }, [clearActiveUserMessageCache, clearActiveUserUploadCache, clearAuth, currentUserExternalId]);

  useEffect(() => {
    registerUnauthorizedHandler(() => {
      runLogoutCleanup();
      setSystemState("error", "Oturum suresi doldu. Lutfen tekrar giris yap.");
    });

    return () => {
      registerUnauthorizedHandler(null);
    };
  }, [runLogoutCleanup, setSystemState]);

  useEffect(() => {
    if (!token) {
      return;
    }

    if (isTokenExpired()) {
      runLogoutCleanup();
      setSystemState("error", "Token suresi doldu. Lutfen tekrar giris yap.");
      return;
    }

    const interval = window.setInterval(() => {
      if (isTokenExpired()) {
        runLogoutCleanup();
        setSystemState("error", "Token suresi doldu. Lutfen tekrar giris yap.");
      }
    }, 30_000);

    return () => {
      window.clearInterval(interval);
    };
  }, [isTokenExpired, runLogoutCleanup, setSystemState, token]);

  if (!token) {
    return <AuthPage />;
  }

  const pathname = typeof window !== "undefined" ? window.location.pathname : "/";
  const isAdminRoute = pathname === "/admin" || pathname.startsWith("/admin/");

  if (isAdminRoute) {
    if (user?.is_admin) {
      return <AdminPage />;
    }
    return (
      <main className="flex min-h-[100dvh] items-center justify-center bg-slate-950 px-4 text-slate-200">
        <section className="w-full max-w-md rounded-2xl border border-rose-500/40 bg-slate-900/80 p-5">
          <h1 className="text-lg font-semibold text-white">Admin yetkisi gerekli</h1>
          <p className="mt-2 text-sm text-slate-300">Bu hesap admin paneline erisemiyor.</p>
          <div className="mt-4 flex gap-2">
            <a
              href="/"
              className="inline-flex h-9 items-center rounded-lg border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200 hover:border-slate-500"
            >
              Ana ekran
            </a>
            <button
              type="button"
              onClick={runLogoutCleanup}
              className="h-9 rounded-lg border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200 hover:border-slate-500"
            >
              Cikis
            </button>
          </div>
        </section>
      </main>
    );
  }

  return <MainAppPage />;
}
