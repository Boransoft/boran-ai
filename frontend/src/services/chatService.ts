import { apiRequest } from "./api";
import type { ChatContextHint } from "../types/context";

export type ChatCitation = {
  file_name: string;
  source_id?: string;
  source_type?: string;
  chunk_count_used?: number;
  page_hint?: string;
};

export type ChatResponse = {
  user_id: string;
  reply: string;
  memory_size?: number;
  context_hits?: number;
  doc_context_hits?: number;
  doc_sources?: string[];
  matched_source_ids?: string[];
  matched_file_names?: string[];
  citations?: ChatCitation[];
  retrieval_fallback_used?: boolean;
};

export function sendChatMessage(params: {
  token: string;
  userId?: string;
  message: string;
  includeReflectionContext?: boolean;
  saveToLongTerm?: boolean;
  contextHint?: ChatContextHint;
}): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chat", {
    method: "POST",
    token: params.token,
    body: {
      user_id: params.userId,
      message: params.message,
      include_reflection_context: params.includeReflectionContext ?? true,
      save_to_long_term: params.saveToLongTerm ?? true,
      context_scope: params.contextHint?.contextScope,
      source_ids: params.contextHint?.sourceIds || [],
      file_names: params.contextHint?.fileNames || [],
      recent_documents:
        params.contextHint?.recentDocuments.map((doc) => ({
          file_name: doc.fileName,
          source_id: doc.sourceId,
          document_id: doc.documentId,
          chunk_count: doc.chunkCount,
          uploaded_at: doc.uploadedAt,
          status: doc.status,
        })) || [],
    },
  });
}
