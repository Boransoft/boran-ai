import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { installLocalStorageMock } from "../test/localStorageMock";
import {
  clearSessionCacheForUser,
  createThrottledStorageWriter,
  messagesStorageKey,
  readJsonFromStorage,
  recentDocsStorageKey,
  removeStorageKey,
  scheduleSessionCacheForUser,
  sessionStorageKey,
  writeJsonToStorage,
} from "./persistence";

describe("persistence", () => {
  beforeEach(() => {
    installLocalStorageMock();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("builds user-scoped storage keys", () => {
    expect(messagesStorageKey("u1")).toBe("boranizm:messages:u1");
    expect(recentDocsStorageKey("u1")).toBe("boranizm:recent_docs:u1");
    expect(sessionStorageKey("u1")).toBe("boranizm:session:u1");
  });

  it("reads valid json and removes malformed payloads", () => {
    const key = "sample";
    writeJsonToStorage(key, { ok: true });
    expect(readJsonFromStorage(key)).toEqual({ ok: true });

    localStorage.setItem("bad", "{broken-json");
    expect(readJsonFromStorage("bad")).toBeNull();
    expect(localStorage.getItem("bad")).toBeNull();
  });

  it("throttles writes and persists latest payload", () => {
    const writer = createThrottledStorageWriter(250);
    const key = "throttle:key";

    writer.schedule(key, { step: 1 });
    writer.schedule(key, { step: 2 });
    vi.advanceTimersByTime(200);
    expect(localStorage.getItem(key)).toBeNull();

    vi.advanceTimersByTime(60);
    expect(readJsonFromStorage(key)).toEqual({ step: 2 });
  });

  it("flushes and cancels scheduled writes", () => {
    const writer = createThrottledStorageWriter(500);
    writer.schedule("flush:key", { now: true });
    writer.flush("flush:key");
    expect(readJsonFromStorage("flush:key")).toEqual({ now: true });

    writer.schedule("cancel:key", { shouldWrite: false });
    writer.cancel("cancel:key");
    vi.advanceTimersByTime(600);
    expect(localStorage.getItem("cancel:key")).toBeNull();
  });

  it("clears session cache and cancels pending session writes", () => {
    const userId = "abc";
    scheduleSessionCacheForUser(userId, { draftText: "pending" });
    clearSessionCacheForUser(userId);
    vi.advanceTimersByTime(1000);
    expect(localStorage.getItem(sessionStorageKey(userId))).toBeNull();
  });

  it("removes storage keys safely", () => {
    localStorage.setItem("x", "1");
    removeStorageKey("x");
    expect(localStorage.getItem("x")).toBeNull();
  });
});
