import AudioPlayer from "./AudioPlayer";
import { toLocalTime } from "../utils/time";
import type { AppMessage, MessageSource } from "../types/message";

export type ChatMessage = AppMessage;

type MessageBubbleProps = {
  message: AppMessage;
  onAudioPlay?: () => void;
  onAudioEnded?: () => void;
};

function roleLabel(type: AppMessage["type"]): string {
  switch (type) {
    case "assistant_text":
    case "assistant_voice":
      return "boranizm";
    case "user_voice":
      return "Sen (ses)";
    case "user_text":
      return "Sen";
    case "error":
      return "Hata";
    default:
      return "Sistem";
  }
}

function bubbleClass(message: AppMessage): string {
  if (message.type === "assistant_text" || message.type === "assistant_voice") {
    return "mr-auto border border-slate-700 bg-slate-800 text-slate-100";
  }

  if (message.type === "user_text" || message.type === "user_voice") {
    return "ml-auto border border-cyan-400/40 bg-cyan-500/20 text-cyan-50";
  }

  if (message.type === "error") {
    return "mx-auto w-full border border-rose-400/40 bg-rose-500/15 text-rose-100";
  }

  return "mx-auto w-full border border-slate-700 bg-slate-900 text-slate-200";
}

function isAssistantMessage(message: AppMessage): boolean {
  return message.type === "assistant_text" || message.type === "assistant_voice";
}

function extractSources(message: AppMessage): MessageSource[] {
  const meta = message.meta;
  if (!meta || typeof meta !== "object" || !("sources" in meta)) {
    return [];
  }
  const raw = meta.sources;
  if (!Array.isArray(raw)) {
    return [];
  }
  const normalized: MessageSource[] = [];
  for (const item of raw) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const candidate = item as Partial<MessageSource>;
    const fileName = typeof candidate.file_name === "string" ? candidate.file_name.trim() : "";
    if (!fileName) {
      continue;
    }
    normalized.push({
      file_name: fileName,
      source_id: typeof candidate.source_id === "string" ? candidate.source_id : undefined,
      source_type: typeof candidate.source_type === "string" ? candidate.source_type : undefined,
      chunk_count_used: typeof candidate.chunk_count_used === "number" ? candidate.chunk_count_used : undefined,
      page_hint: typeof candidate.page_hint === "string" ? candidate.page_hint : undefined,
    });
  }
  return normalized;
}

export default function MessageBubble({ message, onAudioPlay, onAudioEnded }: MessageBubbleProps) {
  const sources = extractSources(message);
  return (
    <article
      className={`w-fit max-w-[92%] break-words rounded-2xl px-3.5 py-2.5 shadow-sm [overflow-wrap:anywhere] sm:max-w-[84%] lg:max-w-[76%] ${bubbleClass(message)}`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-300">{roleLabel(message.type)}</p>

      {message.transcript ? (
        <p className="mt-1 rounded-lg bg-black/20 px-2 py-1 text-[11px] text-slate-300">Transcript: {message.transcript}</p>
      ) : null}

      <p className="mt-1 whitespace-pre-wrap text-[14px] leading-6 sm:text-sm sm:leading-relaxed">{message.content}</p>

      {message.status === "processing" ? (
        <div className="mt-1 flex items-center gap-1.5 text-xs text-amber-200">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-amber-200 border-t-transparent" />
          <span>Islem suruyor...</span>
        </div>
      ) : null}

      {isAssistantMessage(message) && sources.length > 0 ? (
        <div className="mt-2 rounded-lg border border-slate-600/60 bg-slate-900/70 px-2 py-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-300">
            {sources.length > 1 ? "Kaynaklar" : "Kaynak"}
          </p>
          <ul className="mt-1 space-y-1">
            {sources.map((source, index) => (
              <li key={`${source.source_id || source.file_name}-${index}`} className="text-[11px] text-slate-200 sm:text-xs">
                {source.file_name}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {message.audioUrl ? (
        <AudioPlayer
          src={message.audioUrl}
          autoPlay={message.type === "assistant_voice"}
          onPlay={onAudioPlay}
          onEnded={onAudioEnded}
        />
      ) : null}

      <p className="mt-1 text-[10px] text-slate-400">{toLocalTime(message.createdAt)}</p>
    </article>
  );
}
