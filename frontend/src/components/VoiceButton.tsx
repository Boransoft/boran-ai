import type { VoiceStatus } from "../types/voice";

type VoiceButtonProps = {
  isRecording: boolean;
  status: VoiceStatus;
  disabled?: boolean;
  onClick: () => void;
};

export default function VoiceButton({ isRecording, status, disabled, onClick }: VoiceButtonProps) {
  const processing = status === "processing";
  const playing = status === "playing";

  const toneClass = isRecording
    ? "bg-rose-500 text-white hover:bg-rose-400"
    : processing
      ? "bg-amber-500 text-slate-950"
      : playing
        ? "bg-cyan-500 text-slate-950"
        : "bg-emerald-400 text-slate-900 hover:bg-emerald-300";

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || processing}
      title={isRecording ? "Kaydi durdur ve gonder" : "Ses kaydini baslat"}
      className={`h-12 w-12 shrink-0 rounded-full text-[11px] font-semibold transition active:scale-95 touch-manipulation sm:h-14 sm:w-14 ${toneClass} ${
        isRecording ? "animate-pulse" : ""
      } disabled:cursor-not-allowed disabled:opacity-50`}
      aria-label={isRecording ? "Kaydi durdur" : "Ses kaydi baslat"}
    >
      {isRecording ? "Stop" : processing ? "..." : "Mic"}
    </button>
  );
}
