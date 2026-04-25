import { KeyboardEvent } from "react";

import UploadButton from "./UploadButton";
import VoiceButton from "./VoiceButton";
import type { VoiceStatus } from "../types/voice";

type ComposerProps = {
  text: string;
  busy: boolean;
  isRecording: boolean;
  voiceStatus: VoiceStatus;
  uploadInProgress: boolean;
  maxUploadSizeMb: number;
  onTextChange: (value: string) => void;
  onSend: () => void;
  onVoiceToggle: () => void;
  onUploadFiles: (files: File[]) => void;
  onRequestMicPermission: () => void;
};

export default function Composer({
  text,
  busy,
  isRecording,
  voiceStatus,
  uploadInProgress,
  maxUploadSizeMb,
  onTextChange,
  onSend,
  onVoiceToggle,
  onUploadFiles,
  onRequestMicPermission,
}: ComposerProps) {
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  const voiceStateText =
    voiceStatus === "recording"
      ? "Kayit acik"
      : voiceStatus === "processing"
        ? "Ses isleniyor"
        : voiceStatus === "playing"
          ? "Ses oynuyor"
          : "Ses hazir";
  const voiceStateTone =
    voiceStatus === "recording"
      ? "border-rose-500/60 bg-rose-500/15 text-rose-100"
      : voiceStatus === "processing"
        ? "border-amber-500/60 bg-amber-500/15 text-amber-100"
        : voiceStatus === "playing"
          ? "border-cyan-500/60 bg-cyan-500/15 text-cyan-100"
          : "border-slate-600 bg-slate-900/80 text-slate-300";
  const voiceDotTone =
    voiceStatus === "recording"
      ? "bg-rose-300"
      : voiceStatus === "processing"
        ? "bg-amber-300"
        : voiceStatus === "playing"
          ? "bg-cyan-300"
          : "bg-emerald-300";

  return (
    <footer className="sticky bottom-0 z-30 border-t border-slate-700/80 bg-slate-950/95 px-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur sm:px-4 sm:pb-3">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-2.5">
        <div className="flex items-center justify-between gap-2 text-[11px] text-slate-300">
          <button
            type="button"
            onClick={onRequestMicPermission}
            className="h-9 shrink-0 rounded-lg border border-slate-700 bg-slate-900/80 px-3 text-[11px] font-medium text-slate-200 transition hover:border-slate-500 active:scale-95"
          >
            Mikrofon izni
          </button>
          <div className="flex min-w-0 items-center justify-end gap-1.5">
            <span
              className={`inline-flex min-w-0 items-center gap-1.5 truncate rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${voiceStateTone}`}
            >
              <span
                className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${voiceDotTone} ${
                  voiceStatus === "recording" || voiceStatus === "processing" ? "animate-pulse" : ""
                }`}
              />
              <span className="truncate">{voiceStateText}</span>
            </span>
            <span className="hidden text-[11px] text-slate-400 sm:inline">Max: {maxUploadSizeMb} MB</span>
            {uploadInProgress ? (
              <span className="inline-flex shrink-0 rounded-full border border-amber-500/50 bg-amber-500/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-200">
                Yukleme
              </span>
            ) : null}
          </div>
        </div>

        <div className="flex items-end gap-2">
          <textarea
            value={text}
            onChange={(event) => onTextChange(event.target.value)}
            onKeyDown={onKeyDown}
            disabled={busy}
            rows={2}
            placeholder="Mesaj yaz, mikrofona bas veya belge yukle..."
            className="min-h-[52px] max-h-40 flex-1 resize-none rounded-2xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-[16px] leading-6 text-slate-100 outline-none ring-cyan-400/70 transition focus:ring disabled:opacity-60 sm:text-sm sm:leading-5"
          />

          <VoiceButton isRecording={isRecording} status={voiceStatus} disabled={busy} onClick={onVoiceToggle} />
          <UploadButton disabled={uploadInProgress} onSelect={onUploadFiles} maxUploadSizeMb={maxUploadSizeMb} />

          <button
            type="button"
            onClick={onSend}
            disabled={busy || !text.trim()}
            className="h-12 min-w-[58px] shrink-0 rounded-xl bg-cyan-400 px-3.5 text-[13px] font-semibold text-slate-950 transition hover:bg-cyan-300 active:scale-95 touch-manipulation disabled:cursor-not-allowed disabled:opacity-50 sm:h-14 sm:min-w-[64px] sm:px-4"
          >
            Gonder
          </button>
        </div>
      </div>
    </footer>
  );
}
