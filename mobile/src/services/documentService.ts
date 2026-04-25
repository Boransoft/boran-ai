import { apiClient, authHeader, toFileUri } from "./api";

type UploadDocumentParams = {
  token: string;
  file: {
    uri: string;
    name: string;
    type: string;
  };
  category?: string;
  tags?: string;
};

export async function uploadDocument(params: UploadDocumentParams): Promise<void> {
  const form = new FormData();
  form.append("file", {
    uri: toFileUri(params.file.uri),
    name: params.file.name,
    type: params.file.type,
  } as any);
  form.append("category", params.category ?? "general");
  if (params.tags) {
    form.append("tags", params.tags);
  }

  await apiClient.post("/learning/ingest/document", form, {
    headers: {
      ...authHeader(params.token),
      "Content-Type": "multipart/form-data",
    },
  });
}
