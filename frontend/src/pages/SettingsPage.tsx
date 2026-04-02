import { useNavigate } from "react-router-dom";

import { useAuthGuard } from "../hooks/useAuthGuard";
import { resolveApiPath } from "../services/api";
import { useAuthStore } from "../store/authStore";
import { useSettingsStore } from "../store/settingsStore";

export default function SettingsPage() {
  useAuthGuard();

  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  const includeReflectionContext = useSettingsStore((state) => state.includeReflectionContext);
  const preferredAudioFormat = useSettingsStore((state) => state.preferredAudioFormat);
  const setIncludeReflectionContext = useSettingsStore((state) => state.setIncludeReflectionContext);
  const setPreferredAudioFormat = useSettingsStore((state) => state.setPreferredAudioFormat);

  function logout() {
    clearAuth();
    navigate("/login", { replace: true });
  }

  return (
    <section className="page-content">
      <section className="card">
        <h3>User</h3>
        <p>{user?.display_name || user?.username || "Unknown"}</p>
        <p className="muted">{user?.email}</p>
      </section>

      <section className="card form-stack">
        <h3>Chat Defaults</h3>
        <label className="row">
          <span>Include reflection context</span>
          <input
            type="checkbox"
            checked={includeReflectionContext}
            onChange={(e) => setIncludeReflectionContext(e.target.checked)}
          />
        </label>

        <label>
          Preferred audio format
          <select
            value={preferredAudioFormat}
            onChange={(e) => setPreferredAudioFormat(e.target.value as "mp3" | "wav")}
          >
            <option value="mp3">mp3 (recommended mobile)</option>
            <option value="wav">wav (larger files)</option>
          </select>
        </label>
      </section>

      <section className="card">
        <h3>API</h3>
        <p>{resolveApiPath("/")}</p>
      </section>

      <button className="danger" onClick={logout}>
        Logout
      </button>
    </section>
  );
}
