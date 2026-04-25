import type { VoiceStatus } from "../types/voice";
import type { SystemStatus } from "../store/appStore";

type StatusIndicatorProps = {
  voiceStatus: VoiceStatus;
  systemStatus: SystemStatus;
  message: string;
};

const voiceTone: Record<VoiceStatus, string> = {
  idle: "border-slate-600 bg-slate-700/70 text-slate-100",
  recording: "border-rose-400/70 bg-rose-500/30 text-rose-100",
  processing: "border-amber-400/70 bg-amber-500/30 text-amber-100",
  playing: "border-cyan-400/70 bg-cyan-500/30 text-cyan-100",
};

const voiceDotTone: Record<VoiceStatus, string> = {
  idle: "bg-emerald-300",
  recording: "bg-rose-300",
  processing: "bg-amber-300",
  playing: "bg-cyan-300",
};

const voiceLabel: Record<VoiceStatus, string> = {
  idle: "Ses Hazir",
  recording: "Kayit Acik",
  processing: "Ses Isleniyor",
  playing: "Ses Oynuyor",
};

const systemTone: Record<SystemStatus, string> = {
  idle: "text-slate-300",
  loading: "text-amber-300",
  success: "text-emerald-300",
  error: "text-rose-300",
};

export default function StatusIndicator({ voiceStatus, systemStatus, message }: StatusIndicatorProps) {
  return (
    <div className="px-3 py-1 sm:px-4">
      <div className="mx-auto flex w-full max-w-4xl items-center gap-2 rounded-xl border border-slate-800/80 bg-slate-900/60 px-2.5 py-1.5">
        <span
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${voiceTone[voiceStatus]}`}
        >
          <span
            className={`inline-block h-1.5 w-1.5 rounded-full ${voiceDotTone[voiceStatus]} ${
              voiceStatus === "recording" || voiceStatus === "processing" ? "animate-pulse" : ""
            }`}
          />
          {voiceLabel[voiceStatus]}
        </span>
        <span className={`min-w-0 truncate text-[11px] sm:text-xs ${systemTone[systemStatus]}`}>{message}</span>
      </div>
    </div>
  );
}
