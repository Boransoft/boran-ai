import { apiRequest } from "./api";
import type {
  AdminChunkSamplesResponse,
  AdminChunkSummaryResponse,
  AdminConversationMessagesResponse,
  AdminDashboardResponse,
  AdminDocumentDetailResponse,
  AdminListResponse,
  AdminLogDetailResponse,
  AdminConversationItem,
  AdminDocumentItem,
  AdminIngestJobItem,
  AdminLogItem,
  AdminOperationResponse,
} from "../types/admin";

function withQuery(path: string, query: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || String(value).trim() === "") {
      continue;
    }
    params.set(key, String(value));
  }
  const encoded = params.toString();
  return encoded ? `${path}?${encoded}` : path;
}

export function fetchAdminDashboard(token: string): Promise<AdminDashboardResponse> {
  return apiRequest<AdminDashboardResponse>("/admin/dashboard", { token });
}

export function fetchAdminDocuments(params: {
  token: string;
  status?: string;
  q?: string;
  limit?: number;
  offset?: number;
}): Promise<AdminListResponse<AdminDocumentItem>> {
  return apiRequest<AdminListResponse<AdminDocumentItem>>(
    withQuery("/admin/documents", {
      status: params.status,
      q: params.q,
      limit: params.limit,
      offset: params.offset,
    }),
    { token: params.token },
  );
}

export function fetchAdminIngestJobs(params: {
  token: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<AdminListResponse<AdminIngestJobItem>> {
  return apiRequest<AdminListResponse<AdminIngestJobItem>>(
    withQuery("/admin/ingest-jobs", {
      status: params.status,
      limit: params.limit,
      offset: params.offset,
    }),
    { token: params.token },
  );
}

export function fetchAdminConversations(params: {
  token: string;
  limit?: number;
  offset?: number;
}): Promise<AdminListResponse<AdminConversationItem>> {
  return apiRequest<AdminListResponse<AdminConversationItem>>(
    withQuery("/admin/conversations", {
      limit: params.limit,
      offset: params.offset,
    }),
    { token: params.token },
  );
}

export function fetchAdminConversationMessages(params: {
  token: string;
  conversationId: string;
  limit?: number;
}): Promise<AdminConversationMessagesResponse> {
  return apiRequest<AdminConversationMessagesResponse>(
    withQuery(`/admin/conversations/${encodeURIComponent(params.conversationId)}/messages`, {
      limit: params.limit,
    }),
    { token: params.token },
  );
}

export function fetchAdminLogs(params: {
  token: string;
  level?: string;
  component?: string;
  limit?: number;
  offset?: number;
}): Promise<AdminListResponse<AdminLogItem>> {
  return apiRequest<AdminListResponse<AdminLogItem>>(
    withQuery("/admin/logs", {
      level: params.level,
      component: params.component,
      limit: params.limit,
      offset: params.offset,
    }),
    { token: params.token },
  );
}

export function fetchAdminChunkSummary(params: {
  token: string;
  limit?: number;
}): Promise<AdminChunkSummaryResponse> {
  return apiRequest<AdminChunkSummaryResponse>(
    withQuery("/admin/chunks/summary", {
      limit: params.limit,
    }),
    { token: params.token },
  );
}

export function fetchAdminDocumentDetail(params: {
  token: string;
  documentId: string;
}): Promise<AdminDocumentDetailResponse> {
  return apiRequest<AdminDocumentDetailResponse>(`/admin/documents/${encodeURIComponent(params.documentId)}`, {
    token: params.token,
  });
}

export function reprocessAdminDocument(params: {
  token: string;
  documentId: string;
}): Promise<AdminOperationResponse> {
  return apiRequest<AdminOperationResponse>(`/admin/documents/${encodeURIComponent(params.documentId)}/reprocess`, {
    method: "POST",
    token: params.token,
  });
}

export function deleteAdminDocument(params: {
  token: string;
  documentId: string;
}): Promise<AdminOperationResponse> {
  return apiRequest<AdminOperationResponse>(`/admin/documents/${encodeURIComponent(params.documentId)}`, {
    method: "DELETE",
    token: params.token,
  });
}

export function bulkDeleteAdminDocuments(params: {
  token: string;
  documentIds: string[];
}): Promise<AdminOperationResponse> {
  return apiRequest<AdminOperationResponse>("/admin/documents/bulk-delete", {
    method: "POST",
    token: params.token,
    body: params.documentIds,
  });
}

export function bulkReprocessAdminDocuments(params: {
  token: string;
  documentIds: string[];
}): Promise<AdminOperationResponse> {
  return apiRequest<AdminOperationResponse>("/admin/documents/bulk-reprocess", {
    method: "POST",
    token: params.token,
    body: params.documentIds,
  });
}

export function retryAdminIngestJob(params: {
  token: string;
  jobId: string;
}): Promise<AdminOperationResponse> {
  return apiRequest<AdminOperationResponse>(`/admin/ingest-jobs/${encodeURIComponent(params.jobId)}/retry`, {
    method: "POST",
    token: params.token,
  });
}

export function retryFailedAdminIngestJobs(params: {
  token: string;
  limit?: number;
}): Promise<AdminOperationResponse> {
  return apiRequest<AdminOperationResponse>(
    withQuery("/admin/ingest-jobs/retry-failed", {
      limit: params.limit,
    }),
    {
      method: "POST",
      token: params.token,
    },
  );
}

export function deleteAdminConversation(params: {
  token: string;
  conversationId: string;
}): Promise<AdminOperationResponse> {
  return apiRequest<AdminOperationResponse>(`/admin/conversations/${encodeURIComponent(params.conversationId)}`, {
    method: "DELETE",
    token: params.token,
  });
}

export function fetchAdminLogDetail(params: {
  token: string;
  logId: string;
}): Promise<AdminLogDetailResponse> {
  return apiRequest<AdminLogDetailResponse>(`/admin/logs/${encodeURIComponent(params.logId)}`, {
    token: params.token,
  });
}

export function clearAdminLogs(params: {
  token: string;
  level?: string;
  component?: string;
}): Promise<AdminOperationResponse> {
  return apiRequest<AdminOperationResponse>(
    withQuery("/admin/logs/clear", {
      level: params.level,
      component: params.component,
    }),
    {
      method: "POST",
      token: params.token,
    },
  );
}

export function fetchAdminChunkSamples(params: {
  token: string;
  documentId: string;
  limit?: number;
}): Promise<AdminChunkSamplesResponse> {
  return apiRequest<AdminChunkSamplesResponse>(
    withQuery(`/admin/chunks/${encodeURIComponent(params.documentId)}/samples`, {
      limit: params.limit,
    }),
    { token: params.token },
  );
}
