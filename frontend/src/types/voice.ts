export type VoiceStatus = "idle" | "recording" | "processing" | "playing";

export type VoiceTranscribeResponse = {
  status: string;
  user_id: string;
  text: string;
  language: string;
  provider: string;
  audio_file: string;
  upload_mime_type?: string;
};

export type VoiceSpeakResponse = {
  status: string;
  user_id: string;
  text: string;
  provider: string;
  audio_format: string;
  audio_file: string;
  audio_url: string;
  warning?: string;
  tts_voice?: string;
  tts_rate?: string;
  tts_pitch?: string;
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
  upload_mime_type?: string;
  tts_voice?: string;
  tts_rate?: string;
  tts_pitch?: string;
  debug_timing?: Record<string, unknown>;
};

export type VoiceHealthResponse = {
  status: string;
  stt: {
    provider: string;
    ready: boolean;
    detail: string;
    config?: Record<string, unknown>;
  };
  tts: {
    provider: string;
    ready: boolean;
    detail: string;
    config?: Record<string, unknown>;
  };
  preferred_upload_field: string;
  alternative_upload_fields: string[];
  supported_input_mime_types: string[];
};
