import ReactNativeBlobUtil from "react-native-blob-util";

import { apiClient, authHeader, toAbsoluteApiUrl, toFileUri } from "./api";
import { VoiceChatResponse } from "../utils/types";

type VoiceChatParams = {
  token: string;
  audioPath: string;
  language?: string;
};

type DownloadAudioParams = {
  token: string;
  audioUrl: string;
};

function resolveAudioExtension(audioUrl: string): string {
  const cleaned = audioUrl.split("?")[0] || "";
  const parts = cleaned.split(".");
  const extension = parts[parts.length - 1];
  if (!extension || extension.includes("/")) {
    return "mp3";
  }
  return extension.toLowerCase();
}

export async function chatWithVoice(params: VoiceChatParams): Promise<VoiceChatResponse> {
  const form = new FormData();
  form.append("audio", {
    uri: toFileUri(params.audioPath),
    type: "audio/wav",
    name: `voice-${Date.now()}.wav`,
  } as any);
  form.append("save_to_long_term", "true");
  form.append("include_reflection_context", "true");
  form.append("audio_format", "mp3");
  if (params.language) {
    form.append("language", params.language);
  }

  const { data } = await apiClient.post<VoiceChatResponse>("/voice/chat", form, {
    headers: {
      ...authHeader(params.token),
      "Content-Type": "multipart/form-data",
    },
  });

  return data;
}

export async function downloadAudioToCache(params: DownloadAudioParams): Promise<string> {
  const fileExt = resolveAudioExtension(params.audioUrl);
  const response = await ReactNativeBlobUtil.config({
    fileCache: true,
    appendExt: fileExt,
  }).fetch("GET", toAbsoluteApiUrl(params.audioUrl), authHeader(params.token));

  return response.path();
}
