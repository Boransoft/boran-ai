import { create } from "zustand";

type SettingsState = {
  includeReflectionContext: boolean;
  preferredAudioFormat: "mp3" | "wav";
  setIncludeReflectionContext: (value: boolean) => void;
  setPreferredAudioFormat: (value: "mp3" | "wav") => void;
};

const SETTINGS_KEY = "boran_frontend_settings";

function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) {
      return { includeReflectionContext: true, preferredAudioFormat: "mp3" as const };
    }
    const parsed = JSON.parse(raw) as Partial<SettingsState>;
    return {
      includeReflectionContext: parsed.includeReflectionContext ?? true,
      preferredAudioFormat: parsed.preferredAudioFormat ?? "mp3",
    };
  } catch {
    return { includeReflectionContext: true, preferredAudioFormat: "mp3" as const };
  }
}

export const useSettingsStore = create<SettingsState>((set) => ({
  ...loadSettings(),
  setIncludeReflectionContext: (value) => {
    const next = {
      ...loadSettings(),
      includeReflectionContext: value,
    };
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(next));
    set({ includeReflectionContext: value });
  },
  setPreferredAudioFormat: (value) => {
    const next = {
      ...loadSettings(),
      preferredAudioFormat: value,
    };
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(next));
    set({ preferredAudioFormat: value });
  },
}));
