export type MessageType =
  | "user_text"
  | "user_voice_transcript"
  | "assistant_text"
  | "assistant_audio"
  | "system";

export type ChatMessage = {
  id: string;
  type: MessageType;
  text?: string;
  audioUrl?: string;
  createdAt: number;
};

export type AuthUser = {
  id: string;
  external_id: string;
  username?: string | null;
  email?: string | null;
  display_name?: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
};

export type AuthTokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
};

export type ChatResponse = {
  user_id: string;
  reply: string;
  memory_size: number;
};

export type VoiceChatResponse = {
  status: string;
  user_id: string;
  transcript: string;
  reply: string;
  stt_provider: string;
  tts_provider: string;
  audio_format: string;
  audio_file: string;
  audio_url: string;
  warning?: string;
};
