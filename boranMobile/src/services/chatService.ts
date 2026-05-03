import axios from "axios";

import { apiClient, toAbsoluteApiUrl } from "./api";
import { ChatResponse } from "../utils/types";

const CHAT_ENDPOINT_URL = "https://boran-ai.onrender.com/chat";

type SendChatMessageParams = {
  token?: string | null;
  message: string;
  includeReflectionContext?: boolean;
  saveToLongTerm?: boolean;
};

function resolveRequestUrl(url: string | undefined): string {
  if (!url) {
    return CHAT_ENDPOINT_URL;
  }
  if (/^https?:\/\//i.test(url)) {
    return url;
  }
  return toAbsoluteApiUrl(url);
}

function extractDetailText(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map((item) => extractDetailText(item)).filter(Boolean).join(" ");
  }

  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return [record.detail, record.message, record.error]
      .map((item) => extractDetailText(item))
      .filter(Boolean)
      .join(" ");
  }

  return "";
}

export async function sendChatMessage(params: SendChatMessageParams): Promise<ChatResponse> {
  const accessToken = (params.token ?? "").trim();
  const chatUrl = CHAT_ENDPOINT_URL;

  console.log("[chat-service] request:", {
    hasToken: Boolean(accessToken),
    tokenPrefix: accessToken.slice(0, 12),
    url: chatUrl,
  });

  try {
    const headers: Record<string, string> = {};
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    const { data } = await apiClient.post<ChatResponse>(
      chatUrl,
      {
        message: params.message,
      },
      {
        headers,
      },
    );

    return data;
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      const statusCode = error.response?.status;
      const detail = extractDetailText(error.response?.data?.detail ?? error.response?.data) || error.message || "Unknown error";
      const requestUrl = resolveRequestUrl(error.config?.url);
      const statusText = typeof statusCode === "number" ? String(statusCode) : "NO_RESPONSE";
      throw new Error(`Chat request failed | status: ${statusText} | detail: ${detail} | url: ${requestUrl}`);
    }

    throw error;
  }
}
