import { apiRequest } from "./api";

export type ChatResponse = {
  user_id: string;
  reply: string;
  memory_size: number;
  context_hits: number;
};

export function sendChatMessage(params: {
  token: string;
  message: string;
  includeReflectionContext: boolean;
}): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chat", {
    method: "POST",
    token: params.token,
    body: {
      message: params.message,
      include_reflection_context: params.includeReflectionContext,
    },
  });
}
