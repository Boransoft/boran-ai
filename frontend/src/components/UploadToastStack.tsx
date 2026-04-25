import { useEffect } from "react";

import type { UploadStatus } from "../types/upload";

export type UploadToastItem = {
  id: string;
  fileId: string;
  fileName: string;
  status: UploadStatus;
  message: string;
  updatedAt: number;
  autoDismissMs: number | null;
  dismissible: boolean;
};

type UploadToastStackProps = {
  toasts: UploadToastItem[];
  onDismiss: (fileId: string, status: UploadStatus) => void;
};

const titleByStatus: Record<UploadStatus, string> = {
  queued: "Queue",
  uploading: "Upload",
  processing: "Processing",
  success: "Success",
  error: "Error",
};

const toneByStatus: Record<UploadStatus, string> = {
  queued: "border-slate-600/80 bg-slate-900/95 text-slate-200",
  uploading: "border-cyan-500/50 bg-cyan-500/10 text-cyan-100",
  processing: "border-amber-500/50 bg-amber-500/10 text-amber-100",
  success: "border-emerald-500/50 bg-emerald-500/10 text-emerald-100",
  error: "border-rose-500/60 bg-rose-500/10 text-rose-100",
};

function UploadToastCard({
  toast,
  onDismiss,
}: {
  toast: UploadToastItem;
  onDismiss: (fileId: string, status: UploadStatus) => void;
}) {
  useEffect(() => {
    if (!toast.autoDismissMs || toast.autoDismissMs <= 0) {
      return;
    }
    const timer = window.setTimeout(() => {
      onDismiss(toast.fileId, toast.status);
    }, toast.autoDismissMs);
    return () => {
      window.clearTimeout(timer);
    };
  }, [onDismiss, toast.autoDismissMs, toast.fileId, toast.status, toast.updatedAt]);

  return (
    <article
      className={`pointer-events-auto rounded-lg border px-2.5 py-2 shadow-lg backdrop-blur ${toneByStatus[toast.status]}`}
      role="status"
      aria-live={toast.status === "error" ? "assertive" : "polite"}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-[10px] font-semibold uppercase tracking-wide">{titleByStatus[toast.status]}</p>
          <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed">{toast.message}</p>
        </div>
        {toast.dismissible ? (
          <button
            type="button"
            onClick={() => onDismiss(toast.fileId, toast.status)}
            className="rounded-md border border-current/40 px-1.5 py-0.5 text-[10px] font-semibold hover:bg-black/20"
            aria-label={`${toast.fileName} bildirimini kapat`}
          >
            Kapat
          </button>
        ) : null}
      </div>
    </article>
  );
}

export default function UploadToastStack({ toasts, onDismiss }: UploadToastStackProps) {
  if (toasts.length === 0) {
    return null;
  }

  return (
    <aside className="pointer-events-none fixed left-2 right-2 top-[calc(env(safe-area-inset-top)+4.5rem)] z-40 sm:left-auto sm:right-3 sm:top-[calc(env(safe-area-inset-top)+0.8rem)] sm:w-[20rem] md:w-[22rem]">
      <div className="flex max-h-[30vh] flex-col gap-1.5 overflow-y-auto pr-1 sm:max-h-[42vh] sm:gap-2">
        {toasts.map((toast) => (
          <UploadToastCard key={toast.id} toast={toast} onDismiss={onDismiss} />
        ))}
      </div>
    </aside>
  );
}
