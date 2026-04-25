import { create } from "zustand";

import type { VoiceStatus } from "../types/voice";

type VoiceState = {
  status: VoiceStatus;
  provider: string;
  error: string;
  setStatus: (status: VoiceStatus) => void;
  setProvider: (provider: string) => void;
  setError: (error: string) => void;
  reset: () => void;
};

export const useVoiceStore = create<VoiceState>((set) => ({
  status: "idle",
  provider: "",
  error: "",
  setStatus: (status) => set({ status }),
  setProvider: (provider) => set({ provider }),
  setError: (error) => set({ error }),
  reset: () => set({ status: "idle", provider: "", error: "" }),
}));
