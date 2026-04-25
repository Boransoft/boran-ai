import { create } from "zustand";

import type { AppMessage, MessageStatus, MessageType } from "../types/message";
import {
  createThrottledStorageWriter,
  messagesStorageKey,
  readJsonFromStorage,
  removeStorageKey,
} from "./persistence";

const messageWriter = createThrottledStorageWriter();

const MESSAGE_TYPES: MessageType[] = ["user_text", "user_voice", "assistant_text", "assistant_voice", "system", "error"];
const MESSAGE_STATUSES: MessageStatus[] = ["pending", "sent", "processing", "done", "failed"];

function isValidMessageType(value: unknown): value is MessageType {
  return typeof value === "string" && MESSAGE_TYPES.includes(value as MessageType);
}

function isValidMessageStatus(value: unknown): value is MessageStatus {
  return typeof value === "string" && MESSAGE_STATUSES.includes(value as MessageStatus);
}

function normalizeMessage(input: unknown): AppMessage | null {
  if (!input || typeof input !== "object") {
    return null;
  }

  const candidate = input as Partial<AppMessage>;
  if (
    typeof candidate.id !== "string" ||
    !isValidMessageType(candidate.type) ||
    typeof candidate.content !== "string" ||
    typeof candidate.createdAt !== "number" ||
    !isValidMessageStatus(candidate.status)
  ) {
    return null;
  }

  return {
    id: candidate.id,
    type: candidate.type,
    content: candidate.content,
    transcript: typeof candidate.transcript === "string" ? candidate.transcript : undefined,
    audioUrl: typeof candidate.audioUrl === "string" ? candidate.audioUrl : undefined,
    fileName: typeof candidate.fileName === "string" ? candidate.fileName : undefined,
    createdAt: candidate.createdAt,
    status: candidate.status,
    meta: candidate.meta && typeof candidate.meta === "object" ? candidate.meta : undefined,
  };
}

function loadMessages(userId: string): AppMessage[] {
  const parsed = readJsonFromStorage(messagesStorageKey(userId));
  if (!Array.isArray(parsed)) {
    return [];
  }
  return parsed.map(normalizeMessage).filter((item): item is AppMessage => item !== null);
}

function schedulePersistMessages(userId: string, messages: AppMessage[]): void {
  messageWriter.schedule(messagesStorageKey(userId), messages);
}

function clearPersistedMessages(userId: string): void {
  const key = messagesStorageKey(userId);
  messageWriter.cancel(key);
  removeStorageKey(key);
}

type MessageState = {
  activeUserId: string | null;
  messages: AppMessage[];
  setActiveUser: (userId: string | null) => void;
  setMessages: (messages: AppMessage[]) => void;
  addMessage: (message: AppMessage) => void;
  updateMessage: (id: string, patch: Partial<AppMessage>) => void;
  clearMessages: (options?: { clearPersisted?: boolean }) => void;
  clearMessagesForUser: (userId: string) => void;
  clearActiveUserCache: (options?: { clearPersisted?: boolean }) => void;
};

export const useMessageStore = create<MessageState>((set, get) => ({
  activeUserId: null,
  messages: [],
  setActiveUser: (userId) => {
    const nextUserId = (userId || "").trim() || null;
    const previousUserId = get().activeUserId;

    if (previousUserId) {
      messageWriter.flush(messagesStorageKey(previousUserId));
    }

    if (!nextUserId) {
      set({ activeUserId: null, messages: [] });
      return;
    }

    set({
      activeUserId: nextUserId,
      messages: loadMessages(nextUserId),
    });
  },
  setMessages: (messages) =>
    set((state) => {
      if (state.activeUserId) {
        schedulePersistMessages(state.activeUserId, messages);
      }
      return { messages };
    }),
  addMessage: (message) =>
    set((state) => {
      const next = [...state.messages, message];
      if (state.activeUserId) {
        schedulePersistMessages(state.activeUserId, next);
      }
      return { messages: next };
    }),
  updateMessage: (id, patch) =>
    set((state) => {
      let changed = false;
      const next = state.messages.map((message) => {
        if (message.id !== id) {
          return message;
        }
        changed = true;
        return { ...message, ...patch };
      });
      if (!changed) {
        return {};
      }
      if (state.activeUserId) {
        schedulePersistMessages(state.activeUserId, next);
      }
      return { messages: next };
    }),
  clearMessages: (options) =>
    set((state) => {
      const activeUserId = state.activeUserId;
      if (options?.clearPersisted && activeUserId) {
        clearPersistedMessages(activeUserId);
      }
      if (activeUserId) {
        messageWriter.cancel(messagesStorageKey(activeUserId));
      }
      return { messages: [] };
    }),
  clearMessagesForUser: (userId) => {
    const scopedUserId = userId.trim();
    if (!scopedUserId) {
      return;
    }
    clearPersistedMessages(scopedUserId);
    if (get().activeUserId === scopedUserId) {
      set({ messages: [] });
    }
  },
  clearActiveUserCache: (options) => {
    const activeUserId = get().activeUserId;
    if (!activeUserId) {
      set({ messages: [] });
      return;
    }
    if (options?.clearPersisted) {
      clearPersistedMessages(activeUserId);
    } else {
      messageWriter.cancel(messagesStorageKey(activeUserId));
    }
    set({ messages: [] });
  },
}));
