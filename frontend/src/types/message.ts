export type MessageType =
  | "user_text"
  | "user_voice"
  | "assistant_text"
  | "assistant_voice"
  | "system"
  | "error";

export type MessageStatus = "pending" | "sent" | "processing" | "done" | "failed";

export type MessageSource = {
  file_name: string;
  source_id?: string;
  source_type?: string;
  chunk_count_used?: number;
  page_hint?: string;
};

export type MessageMetaValue =
  | string
  | number
  | boolean
  | null
  | MessageSource
  | MessageSource[]
  | Record<string, unknown>;

export type MessageMeta = Record<string, MessageMetaValue>;

export type AppMessage = {
  id: string;
  type: MessageType;
  content: string;
  transcript?: string;
  audioUrl?: string;
  fileName?: string;
  createdAt: number;
  status: MessageStatus;
  meta?: MessageMeta;
};
