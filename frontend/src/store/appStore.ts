import { create } from "zustand";

export type SystemStatus = "idle" | "loading" | "success" | "error";

type AppState = {
  systemStatus: SystemStatus;
  systemMessage: string;
  setSystemState: (status: SystemStatus, message: string) => void;
  clearSystemState: () => void;
};

export const useAppStore = create<AppState>((set) => ({
  systemStatus: "idle",
  systemMessage: "Hazır",
  setSystemState: (systemStatus, systemMessage) => set({ systemStatus, systemMessage }),
  clearSystemState: () => set({ systemStatus: "idle", systemMessage: "Hazır" }),
}));
