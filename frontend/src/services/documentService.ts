import { apiRequest } from "./api";

export type UploadResponse = {
  status: string;
  file: string;
  chunks: number;
  method: string;
  collection: string;
  content_type: string;
  category: string;
  tags: string[];
};

export async function uploadDocument(params: {
  token: string;
  file: File;
  category?: string;
  tags?: string;
}): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("category", params.category || "general");
  if (params.tags) {
    form.append("tags", params.tags);
  }

  return apiRequest<UploadResponse>("/documents/upload", {
    method: "POST",
    token: params.token,
    body: form,
  });
}
