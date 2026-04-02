import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { login, register } from "../services/authService";
import { useAuthStore } from "../store/authStore";

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [emailOrIdentifier, setEmailOrIdentifier] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response =
        mode === "login"
          ? await login(emailOrIdentifier, password)
          : await register({
              username,
              email: emailOrIdentifier,
              password,
              display_name: displayName || undefined,
            });

      setAuth(response.access_token, response.user, response.expires_in);
      navigate("/chat", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-card">
        <h1>boran.ai</h1>
        <p>Mobile-first assistant interface</p>

        <div className="auth-switch">
          <button
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
            type="button"
          >
            Login
          </button>
          <button
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
            type="button"
          >
            Register
          </button>
        </div>

        <form onSubmit={onSubmit} className="form-stack">
          {mode === "register" && (
            <>
              <label>
                Username
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  minLength={3}
                />
              </label>
              <label>
                Display Name
                <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
              </label>
            </>
          )}

          <label>
            {mode === "login" ? "Email or Username" : "Email"}
            <input
              type="text"
              value={emailOrIdentifier}
              onChange={(e) => setEmailOrIdentifier(e.target.value)}
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </label>

          {error ? <p className="error-text">{error}</p> : null}

          <button className="primary" type="submit" disabled={loading}>
            {loading ? "Please wait..." : mode === "login" ? "Login" : "Create Account"}
          </button>
        </form>
      </section>
    </div>
  );
}
