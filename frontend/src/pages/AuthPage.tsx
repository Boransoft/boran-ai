import { FormEvent, useState } from "react";

import { login, register } from "../services/authService";
import { useAppStore } from "../store/appStore";
import { useAuthStore } from "../store/authStore";

export default function AuthPage() {
  const setAuth = useAuthStore((state) => state.setAuth);
  const setSystemState = useAppStore((state) => state.setSystemState);

  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response =
        mode === "login"
          ? await login(identifier, password)
          : await register({
              username,
              email: identifier,
              password,
              display_name: displayName || undefined,
            });

      setAuth(response.access_token, response.user, response.expires_in);
      setSystemState("success", "Giris basarili.");
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Kimlik dogrulama basarisiz.";
      setError(detail);
      setSystemState("error", detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-[100dvh] items-center justify-center overflow-y-auto bg-slate-950 px-3 pb-[max(1rem,env(safe-area-inset-bottom))] pt-[max(1rem,env(safe-area-inset-top))] sm:px-4">
      <section className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900/90 p-4 shadow-xl sm:p-6">
        <h1 className="text-xl font-semibold text-white sm:text-2xl">boranizm</h1>
        <p className="mt-1 text-xs text-slate-300 sm:text-sm">Tek ekran: chat + voice + belge ogrenme</p>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setMode("login")}
            className={`h-10 rounded-xl border px-3 text-sm font-medium transition active:scale-95 ${
              mode === "login"
                ? "border-cyan-400 bg-cyan-400/20 text-cyan-100"
                : "border-slate-600 bg-slate-800 text-slate-300"
            }`}
          >
            Login
          </button>
          <button
            type="button"
            onClick={() => setMode("register")}
            className={`h-10 rounded-xl border px-3 text-sm font-medium transition active:scale-95 ${
              mode === "register"
                ? "border-cyan-400 bg-cyan-400/20 text-cyan-100"
                : "border-slate-600 bg-slate-800 text-slate-300"
            }`}
          >
            Register
          </button>
        </div>

        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          {mode === "register" ? (
            <>
              <label className="block text-sm text-slate-200">
                Username
                <input
                  className="mt-1 h-11 w-full rounded-xl border border-slate-600 bg-slate-800 px-3 text-white outline-none ring-cyan-400 transition focus:ring"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  required
                  minLength={3}
                />
              </label>

              <label className="block text-sm text-slate-200">
                Display Name
                <input
                  className="mt-1 h-11 w-full rounded-xl border border-slate-600 bg-slate-800 px-3 text-white outline-none ring-cyan-400 transition focus:ring"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                />
              </label>
            </>
          ) : null}

          <label className="block text-sm text-slate-200">
            {mode === "login" ? "Email veya Username" : "Email"}
            <input
              className="mt-1 h-11 w-full rounded-xl border border-slate-600 bg-slate-800 px-3 text-white outline-none ring-cyan-400 transition focus:ring"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              required
            />
          </label>

          <label className="block text-sm text-slate-200">
            Password
            <input
              type="password"
              className="mt-1 h-11 w-full rounded-xl border border-slate-600 bg-slate-800 px-3 text-white outline-none ring-cyan-400 transition focus:ring"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
            />
          </label>

          {error ? <p className="text-sm text-rose-300">{error}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="h-11 w-full rounded-xl bg-cyan-400 px-4 font-semibold text-slate-900 transition hover:bg-cyan-300 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? "Bekleyin..." : mode === "login" ? "Login" : "Create Account"}
          </button>
        </form>
      </section>
    </main>
  );
}

