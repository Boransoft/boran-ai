import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AppMessage } from "../types/message";
import { installLocalStorageMock } from "../test/localStorageMock";
import { messagesStorageKey } from "./persistence";
import { useMessageStore } from "./messageStore";

function sampleMessage(id: string, content: string): AppMessage {
  return {
    id,
    type: "assistant_text",
    content,
    createdAt: Date.now(),
    status: "done",
  };
}

describe("messageStore persistence", () => {
  beforeEach(() => {
    installLocalStorageMock();
    vi.useFakeTimers();
    useMessageStore.setState({ activeUserId: null, messages: [] });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    useMessageStore.setState({ activeUserId: null, messages: [] });
  });

  it("loads only valid persisted messages for active user", () => {
    const key = messagesStorageKey("u1");
    localStorage.setItem(
      key,
      JSON.stringify([
        sampleMessage("m1", "valid"),
        { id: 1, type: "assistant_text", content: "invalid", createdAt: 0, status: "done" },
      ]),
    );

    useMessageStore.getState().setActiveUser("u1");

    expect(useMessageStore.getState().activeUserId).toBe("u1");
    expect(useMessageStore.getState().messages).toHaveLength(1);
    expect(useMessageStore.getState().messages[0].id).toBe("m1");
  });

  it("flushes previous user messages when switching active user", () => {
    useMessageStore.getState().setActiveUser("u1");
    useMessageStore.getState().addMessage(sampleMessage("m1", "hello"));

    expect(localStorage.getItem(messagesStorageKey("u1"))).toBeNull();

    useMessageStore.getState().setActiveUser("u2");

    const persisted = localStorage.getItem(messagesStorageKey("u1"));
    expect(persisted).not.toBeNull();
    expect(JSON.parse(persisted as string)).toHaveLength(1);
    expect(useMessageStore.getState().activeUserId).toBe("u2");
    expect(useMessageStore.getState().messages).toHaveLength(0);
  });

  it("clears in-memory messages without deleting persisted history by default", () => {
    const key = messagesStorageKey("u1");
    localStorage.setItem(key, JSON.stringify([sampleMessage("m1", "persisted")]));

    useMessageStore.getState().setActiveUser("u1");
    useMessageStore.getState().clearActiveUserCache();

    expect(useMessageStore.getState().messages).toHaveLength(0);
    expect(localStorage.getItem(key)).not.toBeNull();
  });

  it("removes persisted history when clearPersisted is true", () => {
    const key = messagesStorageKey("u1");
    localStorage.setItem(key, JSON.stringify([sampleMessage("m1", "persisted")]));

    useMessageStore.getState().setActiveUser("u1");
    useMessageStore.getState().clearActiveUserCache({ clearPersisted: true });

    expect(useMessageStore.getState().messages).toHaveLength(0);
    expect(localStorage.getItem(key)).toBeNull();
  });
});
