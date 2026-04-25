import { apiClient, authHeader } from "./api";
import { ChatResponse } from "../utils/types";

type SendChatMessageParams = {
  token: string;
  message: string;
  includeReflectionContext?: boolean;
  saveToLongTerm?: boolean;
};

export async function sendChatMessage(params: SendChatMessageParams): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>(
    "/chat",
    {
      message: params.message,
      include_reflection_context: params.includeReflectionContext ?? true,
      save_to_long_term: params.saveToLongTerm ?? true,
    },
    {
      headers: authHeader(params.token),
    },
  );
  return data;
}
