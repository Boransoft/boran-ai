export type UploadedDocumentStatus = "success" | "error";

export type UploadedDocument = {
  fileName: string;
  sourceId: string;
  documentId: string;
  chunkCount: number;
  uploadedAt: number;
  status: UploadedDocumentStatus;
};

export type UploadResult = {
  status: string;
  details: Record<string, unknown>;
};

export type ChatContextHint = {
  contextScope: "uploaded_documents" | "global";
  sourceIds: string[];
  fileNames: string[];
  recentDocuments: UploadedDocument[];
};

export type SystemMessageMeta = {
  code:
    | "upload_queued"
    | "uploading"
    | "upload_success"
    | "upload_error"
    | "retrieval_no_hit"
    | "retrieval_guidance";
  fileName?: string;
  sourceId?: string;
  chunkCount?: number;
};
