export type UploadStatus = "queued" | "uploading" | "processing" | "success" | "error";

export type UploadFileState = {
  id: string;
  fileName: string;
  status: UploadStatus;
  progress: number;
  sizeBytes: number;
  mimeType: string;
  createdAt: number;
  errorMessage: string;
  sourceId: string;
  documentId: string;
  chunkCount: number;
  uploadedAt: number | null;
  backendResponse: Record<string, unknown> | null;
};
