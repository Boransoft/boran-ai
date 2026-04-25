import { resolveApiPath } from "./api";
import type { UploadResult } from "../types/context";
import { SystemMessages } from "../utils/systemMessages";

export async function uploadDocument(params: {
  token: string;
  file: File;
  category?: string;
  tags?: string;
  onProgress?: (progress: number) => void;
}): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("category", params.category || "general");
  if (params.tags) {
    form.append("tags", params.tags);
  }

  return new Promise<UploadResult>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", resolveApiPath("/learning/ingest/document"));
    xhr.responseType = "arraybuffer";
    xhr.setRequestHeader("Authorization", `Bearer ${params.token}`);

    xhr.upload.onprogress = (event) => {
      if (!params.onProgress || !event.lengthComputable) {
        return;
      }
      const progress = Math.round((event.loaded / event.total) * 100);
      params.onProgress(Math.max(0, Math.min(100, progress)));
    };

    xhr.onerror = () => reject(new Error(`${SystemMessages.connectionError} (${SystemMessages.documentUploadFailed})`));

    xhr.onload = () => {
      let responseText = "";
      if (xhr.response instanceof ArrayBuffer) {
        responseText = new TextDecoder("utf-8").decode(xhr.response);
      } else {
        responseText = xhr.responseText || "";
      }

      let payload: unknown = {};
      try {
        payload = responseText ? (JSON.parse(responseText) as unknown) : {};
      } catch {
        payload = {};
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload as UploadResult);
        return;
      }

      const detail =
        typeof payload === "object" &&
        payload &&
        "detail" in payload &&
        typeof (payload as { detail?: unknown }).detail === "string"
          ? String((payload as { detail: string }).detail)
          : `${SystemMessages.documentUploadFailed} (${xhr.status})`;
      reject(new Error(detail));
    };

    xhr.send(form);
  });
}
