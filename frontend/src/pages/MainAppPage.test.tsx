// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import MainAppPage from "./MainAppPage";
import { useAppStore } from "../store/appStore";
import { useAuthStore } from "../store/authStore";
import { useMessageStore } from "../store/messageStore";
import { sessionStorageKey, recentDocsStorageKey, messagesStorageKey } from "../store/persistence";
import { installLocalStorageMock } from "../test/localStorageMock";
import { useUploadStore } from "../store/uploadStore";
import { useVoiceStore } from "../store/voiceStore";

vi.mock("../components/TopBar", () => ({
  default: ({ onLogout }: { onLogout: () => void }) => (
    <button data-testid="logout-button" onClick={onLogout}>
      logout
    </button>
  ),
}));

vi.mock("../components/StatusIndicator", () => ({
  default: ({ message }: { message: string }) => <div data-testid="status-message">{message}</div>,
}));

vi.mock("../components/MessageList", () => ({
  default: ({ messages }: { messages: Array<{ id: string; content: string }> }) => (
    <ul data-testid="message-list">
      {messages.map((message) => (
        <li key={message.id}>{message.content}</li>
      ))}
    </ul>
  ),
}));

vi.mock("../components/Composer", () => ({
  default: ({
    text,
    onTextChange,
  }: {
    text: string;
    onTextChange: (next: string) => void;
  }) => (
    <input
      data-testid="composer-input"
      value={text}
      onChange={(event) => onTextChange((event.target as HTMLInputElement).value)}
    />
  ),
}));

vi.mock("../hooks/useRecorder", () => ({
  useRecorder: () => ({
    error: "",
    isRecording: false,
    isSupported: true,
    supportMessage: "",
    mimeType: "audio/webm",
    requestPermission: vi.fn(async () => true),
    startRecording: vi.fn(async () => true),
    stopRecording: vi.fn(async () => null),
  }),
}));

vi.mock("../services/chatService", () => ({
  sendChatMessage: vi.fn(),
}));

vi.mock("../services/documentService", () => ({
  uploadDocument: vi.fn(),
}));

vi.mock("../services/voiceService", () => ({
  chatWithVoice: vi.fn(),
  getAudioObjectUrl: vi.fn(),
}));

function setAuthUser(externalId: string): void {
  useAuthStore.setState({
    token: "token-1",
    user: {
      id: `id-${externalId}`,
      external_id: externalId,
      username: externalId,
    },
    expiresAt: Date.now() + 60_000,
  });
}

describe("MainAppPage component persistence", () => {
  beforeEach(() => {
    installLocalStorageMock();
    useAppStore.setState({
      systemStatus: "idle",
      systemMessage: "Hazır",
    });
    useVoiceStore.setState({
      status: "idle",
      provider: "",
      error: "",
    });
    useMessageStore.setState({
      activeUserId: null,
      messages: [],
    });
    useUploadStore.setState({
      activeUserId: null,
      files: [],
      inProgress: false,
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("restores session draft text from user-scoped cache", async () => {
    setAuthUser("u1");
    localStorage.setItem(
      sessionStorageKey("u1"),
      JSON.stringify({
        version: 1,
        draftText: "cached draft",
        systemStatus: "success",
        systemMessage: "cached status",
        voiceStatus: "idle",
        voiceProvider: "",
        voiceError: "",
        updatedAt: Date.now(),
      }),
    );

    render(<MainAppPage />);

    await waitFor(() => {
      const input = screen.getByTestId("composer-input") as HTMLInputElement;
      expect(input.value).toBe("cached draft");
    });
    expect(screen.getByTestId("status-message").textContent).toBe("cached status");
  });

  it("switches message context when authenticated user changes", async () => {
    localStorage.setItem(
      messagesStorageKey("u1"),
      JSON.stringify([
        {
          id: "m-u1",
          type: "assistant_text",
          content: "u1 message",
          createdAt: 1,
          status: "done",
        },
      ]),
    );
    localStorage.setItem(
      messagesStorageKey("u2"),
      JSON.stringify([
        {
          id: "m-u2",
          type: "assistant_text",
          content: "u2 message",
          createdAt: 2,
          status: "done",
        },
      ]),
    );

    setAuthUser("u1");
    render(<MainAppPage />);

    await waitFor(() => {
      expect(screen.getByText("u1 message")).toBeTruthy();
    });

    setAuthUser("u2");

    await waitFor(() => {
      expect(screen.getByText("u2 message")).toBeTruthy();
    });
  });

  it("logout clears session and recent docs cache but keeps persisted messages by default", async () => {
    setAuthUser("u1");
    localStorage.setItem(
      messagesStorageKey("u1"),
      JSON.stringify([
        {
          id: "m1",
          type: "assistant_text",
          content: "persist me",
          createdAt: 1,
          status: "done",
        },
      ]),
    );
    localStorage.setItem(
      recentDocsStorageKey("u1"),
      JSON.stringify([
        {
          id: "f1",
          fileName: "doc.pdf",
          status: "success",
          progress: 100,
          sizeBytes: 128,
          mimeType: "application/pdf",
          createdAt: 1,
          errorMessage: "",
          sourceId: "doc.pdf",
          documentId: "d1",
          chunkCount: 1,
          uploadedAt: 1,
          backendResponse: null,
        },
      ]),
    );
    localStorage.setItem(
      sessionStorageKey("u1"),
      JSON.stringify({
        version: 1,
        draftText: "draft",
        systemStatus: "idle",
        systemMessage: "idle",
        voiceStatus: "idle",
        voiceProvider: "",
        voiceError: "",
        updatedAt: Date.now(),
      }),
    );

    render(<MainAppPage />);

    await waitFor(() => {
      expect(useUploadStore.getState().activeUserId).toBe("u1");
      expect(useMessageStore.getState().activeUserId).toBe("u1");
    });

    fireEvent.click(screen.getByTestId("logout-button"));

    await waitFor(() => {
      expect(useAuthStore.getState().token).toBeNull();
    });
    expect(localStorage.getItem(sessionStorageKey("u1"))).toBeNull();
    expect(localStorage.getItem(recentDocsStorageKey("u1"))).toBeNull();
    expect(localStorage.getItem(messagesStorageKey("u1"))).not.toBeNull();
  });
});
