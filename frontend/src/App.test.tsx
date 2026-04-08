// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { useAppStore } from "./store/appStore";
import { useAuthStore } from "./store/authStore";
import { useMessageStore } from "./store/messageStore";
import { messagesStorageKey, recentDocsStorageKey, sessionStorageKey } from "./store/persistence";
import { useUploadStore } from "./store/uploadStore";
import { installLocalStorageMock } from "./test/localStorageMock";

let unauthorizedHandler: (() => void) | null = null;

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

vi.mock("./pages/AuthPage", () => ({
  default: () => <div data-testid="auth-page">auth</div>,
}));

vi.mock("./pages/MainAppPage", () => ({
  default: () => <div data-testid="main-page">main</div>,
}));

vi.mock("./services/api", () => ({
  registerUnauthorizedHandler: (handler: (() => void) | null) => {
    unauthorizedHandler = handler;
  },
}));

function setAuthState(externalId: string, expiresAt: number): void {
  useAuthStore.setState({
    token: "token-1",
    user: {
      id: `id-${externalId}`,
      external_id: externalId,
      username: externalId,
    },
    expiresAt,
  });
}

describe("App session cleanup", () => {
  beforeEach(() => {
    installLocalStorageMock();
    unauthorizedHandler = null;
    useAppStore.setState({
      systemStatus: "idle",
      systemMessage: "Hazır",
    });
    useAuthStore.setState({
      token: null,
      user: null,
      expiresAt: 0,
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

  it("handles unauthorized callback with scoped cache cleanup", async () => {
    const externalId = "u1";
    setAuthState(externalId, Date.now() + 120_000);
    useMessageStore.setState({ activeUserId: externalId, messages: [] });
    useUploadStore.setState({ activeUserId: externalId, files: [], inProgress: false });

    localStorage.setItem(sessionStorageKey(externalId), JSON.stringify({ version: 1 }));
    localStorage.setItem(recentDocsStorageKey(externalId), JSON.stringify([]));
    localStorage.setItem(messagesStorageKey(externalId), JSON.stringify([]));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("main-page")).toBeTruthy();
      expect(typeof unauthorizedHandler).toBe("function");
    });

    act(() => {
      unauthorizedHandler?.();
    });

    await waitFor(() => {
      expect(screen.getByTestId("auth-page")).toBeTruthy();
      expect(useAuthStore.getState().token).toBeNull();
    });
    expect(localStorage.getItem(sessionStorageKey(externalId))).toBeNull();
    expect(localStorage.getItem(recentDocsStorageKey(externalId))).toBeNull();
    expect(localStorage.getItem(messagesStorageKey(externalId))).not.toBeNull();
    expect(useAppStore.getState().systemStatus).toBe("error");
    expect(useAppStore.getState().systemMessage).toContain("Oturum suresi doldu");
  });

  it("cleans up on already expired token", async () => {
    const externalId = "u2";
    setAuthState(externalId, Date.now() - 1_000);
    useMessageStore.setState({ activeUserId: externalId, messages: [] });
    useUploadStore.setState({ activeUserId: externalId, files: [], inProgress: false });

    localStorage.setItem(sessionStorageKey(externalId), JSON.stringify({ version: 1 }));
    localStorage.setItem(recentDocsStorageKey(externalId), JSON.stringify([]));
    localStorage.setItem(messagesStorageKey(externalId), JSON.stringify([]));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("auth-page")).toBeTruthy();
      expect(useAuthStore.getState().token).toBeNull();
    });
    expect(localStorage.getItem(sessionStorageKey(externalId))).toBeNull();
    expect(localStorage.getItem(recentDocsStorageKey(externalId))).toBeNull();
    expect(localStorage.getItem(messagesStorageKey(externalId))).not.toBeNull();
    expect(useAppStore.getState().systemStatus).toBe("error");
    expect(useAppStore.getState().systemMessage).toContain("Token suresi doldu");
  });
});
