import type { UploadFileState, UploadStatus } from "../types/upload";

type UploadStatusItemProps = {
  file: UploadFileState;
};

const statusLabels: Record<UploadStatus, string> = {
  queued: "kuyrukta",
  uploading: "yukleniyor",
  processing: "isleniyor",
  success: "tamamlandi",
  error: "hata",
};

const statusColors: Record<UploadStatus, string> = {
  queued: "bg-slate-700 text-slate-100",
  uploading: "bg-cyan-500/30 text-cyan-100",
  processing: "bg-amber-500/30 text-amber-100",
  success: "bg-emerald-500/30 text-emerald-100",
  error: "bg-rose-500/30 text-rose-100",
};

function formatSize(sizeBytes: number): string {
  if (sizeBytes >= 1024 * 1024) {
    return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  if (sizeBytes >= 1024) {
    return `${Math.round(sizeBytes / 1024)} KB`;
  }
  return `${sizeBytes} B`;
}

function toStringSafe(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function toChunkCount(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.max(0, value);
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return Math.max(0, parsed);
    }
  }
  return 0;
}

export default function UploadStatusItem({ file }: UploadStatusItemProps) {
  const details =
    file.backendResponse && typeof file.backendResponse === "object" && typeof file.backendResponse.details === "object"
      ? (file.backendResponse.details as Record<string, unknown>)
      : null;

  const backendFileName = toStringSafe(details?.file_name) || file.fileName;
  const backendStatus = toStringSafe(details?.status) || toStringSafe(file.backendResponse?.status) || "";
  const backendChunks = file.chunkCount > 0 ? file.chunkCount : toChunkCount(details?.chunks || details?.chunk_count);

  return (
    <article className="rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-xs font-medium text-slate-100" title={file.fileName}>
          {file.fileName}
        </p>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${statusColors[file.status]}`}>
          {statusLabels[file.status]}
        </span>
      </div>

      <div className="mt-1 flex items-center justify-between text-[11px] text-slate-400">
        <span>{formatSize(file.sizeBytes)}</span>
        <span>{file.progress}%</span>
      </div>

      {(file.status === "uploading" || file.status === "processing") && (
        <div className="mt-1 h-1.5 rounded-full bg-slate-800">
          <div className="h-full rounded-full bg-cyan-400 transition-all" style={{ width: `${file.progress}%` }} />
        </div>
      )}

      {file.status === "processing" && (
        <div className="mt-1 flex items-center gap-1.5 text-[11px] text-amber-200">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-amber-200 border-t-transparent" />
          <span>Belge isleniyor...</span>
        </div>
      )}

      {file.status === "success" && (
        <p className="mt-1 text-[11px] text-emerald-300">
          Tamamlandi: {backendFileName}
          {backendChunks > 0 ? ` | chunks: ${backendChunks}` : ""}
          {backendStatus ? ` | durum: ${backendStatus}` : ""}
        </p>
      )}

      {file.status === "error" && (
        <p className="mt-1 text-[11px] text-rose-300">
          Hata: {file.errorMessage || "Belge yuklenemedi."}
        </p>
      )}
    </article>
  );
}
