import { apiRequest, fetchBinary } from "./api";

export type VoiceChatResponse = {
  status: string;
  user_id: string;
  transcript: string;
  reply: string;
  audio_url: string;
  audio_file: string;
  audio_format: string;
  stt_provider: string;
  tts_provider: string;
  warning?: string;
};

export async function transcribeAudio(params: {
  token: string;
  file: File;
  language?: string;
}) {
  const form = new FormData();
  form.append("audio", params.file);
  if (params.language) form.append("language", params.language);

  return apiRequest<{ text: string; language: string; provider: string }>("/voice/transcribe", {
    method: "POST",
    token: params.token,
    body: form,
  });
}

export async function chatWithVoice(params: {
  token: string;
  file: File;
  language?: string;
  includeReflectionContext?: boolean;
  audioFormat?: "mp3" | "wav";
}) {
  const form = new FormData();
  form.append("audio", params.file);
  if (params.language) form.append("language", params.language);
  form.append("save_to_long_term", "true");
  if (typeof params.includeReflectionContext === "boolean") {
    form.append("include_reflection_context", String(params.includeReflectionContext));
  }
  if (params.audioFormat) {
    form.append("audio_format", params.audioFormat);
  }

  return apiRequest<VoiceChatResponse>("/voice/chat", {
    method: "POST",
    token: params.token,
    body: form,
  });
}

export async function playAudio(params: { token: string; url: string }): Promise<string> {
  const blob = await fetchBinary(params.url, params.token);
  return URL.createObjectURL(blob);
}
