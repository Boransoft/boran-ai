import type {
  VoiceChatResponse,
  VoiceHealthResponse,
  VoiceSpeakResponse,
  VoiceTranscribeResponse,
} from "../types/voice";

import { apiRequest, fetchBinary } from "./api";

export async function voiceHealth(token: string): Promise<VoiceHealthResponse> {
  return apiRequest<VoiceHealthResponse>("/voice/health", { token });
}

export async function transcribeAudio(params: {
  token: string;
  file: File;
  language?: string;
}): Promise<VoiceTranscribeResponse> {
  const form = new FormData();
  form.append("audio", params.file);
  if (params.language) {
    form.append("language", params.language);
  }

  return apiRequest<VoiceTranscribeResponse>("/voice/transcribe", {
    method: "POST",
    token: params.token,
    body: form,
  });
}

export async function speakText(params: {
  token: string;
  text: string;
  audioFormat?: "mp3" | "wav";
}): Promise<VoiceSpeakResponse> {
  return apiRequest<VoiceSpeakResponse>("/voice/speak", {
    method: "POST",
    token: params.token,
    body: {
      text: params.text,
      audio_format: params.audioFormat ?? "mp3",
      stream_audio: false,
    },
  });
}

export async function chatWithVoice(params: {
  token: string;
  file: File;
  language?: string;
  includeReflectionContext?: boolean;
  audioFormat?: "mp3" | "wav";
  debugTiming?: boolean;
}): Promise<VoiceChatResponse> {
  const form = new FormData();
  form.append("audio", params.file);
  if (params.language) {
    form.append("language", params.language);
  }

  form.append("save_to_long_term", "true");
  if (typeof params.includeReflectionContext === "boolean") {
    form.append("include_reflection_context", String(params.includeReflectionContext));
  }

  form.append("audio_format", params.audioFormat ?? "mp3");

  const path = params.debugTiming ? "/voice/chat?debug_timing=true" : "/voice/chat";
  return apiRequest<VoiceChatResponse>(path, {
    method: "POST",
    token: params.token,
    body: form,
  });
}

export async function getAudioObjectUrl(params: {
  token: string;
  audioPath: string;
}): Promise<string> {
  const blob = await fetchBinary(params.audioPath, params.token);
  return URL.createObjectURL(blob);
}

export async function playAudio(params: {
  token: string;
  url: string;
}): Promise<string> {
  return getAudioObjectUrl({ token: params.token, audioPath: params.url });
}
