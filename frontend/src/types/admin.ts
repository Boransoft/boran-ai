export type AdminDashboardCounts = {
  users: number;
  documents: number;
  chunks: number;
  ingest_active: number;
  ingest_pending: number;
  ingest_failed: number;
};

export type AdminDocumentItem = {
  id: string;
  document_id: string;
  source_id: string;
  user_id: string;
  file_name: string;
  source_type: string;
  mime_type: string;
  file_size: number;
  chunk_count: number;
  status: string;
  uploaded_at: string;
  category: string;
  tags: string | string[];
};

export type AdminIngestJobItem = {
  id: string;
  status: string;
  stage: string;
  document_id: string;
  file_name: string;
  started_at: string;
  completed_at: string;
  retry_count: number;
  error_message: string;
};

export type AdminConversationItem = {
  conversation_id: string;
  user_id: string;
  title: string;
  last_message_at: string;
  created_at: string;
};

export type AdminConversationMessageItem = {
  id: string;
  role: string;
  content: string;
  created_at: string;
};

export type AdminLogItem = {
  id: string;
  level: string;
  component: string;
  message: string;
  timestamp: string;
  related?: AdminRelatedRefs;
};

export type AdminChunkSummaryItem = {
  document_id: string;
  file_name: string;
  source_id: string;
  chunk_count: number;
};

export type AdminChunkSampleItem = {
  chunk_index: number;
  content: string;
};

export type AdminRelatedRefs = {
  document_id?: string;
  source_id?: string;
  conversation_id?: string;
  job_id?: string;
};

export type AdminListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminDashboardResponse = {
  counts: AdminDashboardCounts;
  recent_errors: AdminLogItem[];
  recent_conversations: AdminConversationItem[];
  recent_documents: AdminDocumentItem[];
  tables: Record<string, boolean>;
  missing_tables: string[];
};

export type AdminConversationMessagesResponse = {
  items: AdminConversationMessageItem[];
  total: number;
};

export type AdminChunkSummaryResponse = {
  items: AdminChunkSummaryItem[];
  total_chunks: number;
};

export type AdminDocumentDetailResponse = {
  document: AdminDocumentItem;
  source: string;
  file_path: string;
};

export type AdminChunkSamplesResponse = {
  document_id: string;
  items: AdminChunkSampleItem[];
  total: number;
};

export type AdminOperationResponse = {
  status: string;
  message: string;
  [key: string]: unknown;
};

export type AdminLogDetailResponse = AdminLogItem & {
  raw: Record<string, unknown>;
};
