import UploadStatusItem from "./UploadStatusItem";
import type { UploadFileState } from "../types/upload";

type UploadQueueProps = {
  files: UploadFileState[];
};

export default function UploadQueue({ files }: UploadQueueProps) {
  if (files.length === 0) {
    return null;
  }

  const queued = files.filter((file) => file.status === "queued").length;
  const uploading = files.filter((file) => file.status === "uploading").length;
  const processing = files.filter((file) => file.status === "processing").length;
  const success = files.filter((file) => file.status === "success").length;
  const error = files.filter((file) => file.status === "error").length;

  return (
    <section className="rounded-2xl border border-slate-700/80 bg-slate-950/80 p-2">
      <div className="mb-2 flex items-center justify-between text-[11px] text-slate-300">
        <p className="font-semibold text-slate-100">Upload Queue</p>
        <p>
          q:{queued} u:{uploading} p:{processing} ok:{success} err:{error}
        </p>
      </div>

      <div className="grid max-h-40 gap-2 overflow-y-auto pr-1">
        {files.map((file) => (
          <UploadStatusItem key={file.id} file={file} />
        ))}
      </div>
    </section>
  );
}
