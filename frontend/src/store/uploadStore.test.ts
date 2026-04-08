import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { installLocalStorageMock } from "../test/localStorageMock";
import { recentDocsStorageKey } from "./persistence";
import { useUploadStore } from "./uploadStore";

function mockFile(name: string, size: number, type: string): File {
  return { name, size, type } as unknown as File;
}

describe("uploadStore persistence", () => {
  beforeEach(() => {
    installLocalStorageMock();
    vi.useFakeTimers();
    useUploadStore.setState({ activeUserId: null, files: [], inProgress: false });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    useUploadStore.setState({ activeUserId: null, files: [], inProgress: false });
  });

  it("normalizes interrupted uploads restored from storage", () => {
    localStorage.setItem(
      recentDocsStorageKey("u1"),
      JSON.stringify([
        {
          id: "f1",
          fileName: "doc.pdf",
          status: "uploading",
          progress: 140,
          sizeBytes: 42,
          mimeType: "application/pdf",
          createdAt: 1,
          errorMessage: "",
        },
      ]),
    );

    useUploadStore.getState().setActiveUser("u1");
    const restored = useUploadStore.getState().files[0];

    expect(restored.status).toBe("error");
    expect(restored.progress).toBe(100);
    expect(restored.errorMessage).toContain("Yukleme kesintiye ugradi");
    expect(useUploadStore.getState().inProgress).toBe(false);
  });

  it("flushes queued uploads of previous user on user switch", () => {
    useUploadStore.getState().setActiveUser("u1");
    useUploadStore.getState().enqueueFiles([mockFile("a.pdf", 100, "application/pdf")]);

    expect(localStorage.getItem(recentDocsStorageKey("u1"))).toBeNull();

    useUploadStore.getState().setActiveUser("u2");

    const persisted = localStorage.getItem(recentDocsStorageKey("u1"));
    expect(persisted).not.toBeNull();
    expect(JSON.parse(persisted as string)).toHaveLength(1);
    expect(useUploadStore.getState().activeUserId).toBe("u2");
  });

  it("clears persisted recent docs for active user on cache clear", () => {
    const key = recentDocsStorageKey("u1");
    localStorage.setItem(key, JSON.stringify([{ id: "f1" }]));

    useUploadStore.getState().setActiveUser("u1");
    useUploadStore.getState().clearActiveUserCache();

    expect(useUploadStore.getState().files).toHaveLength(0);
    expect(useUploadStore.getState().inProgress).toBe(false);
    expect(localStorage.getItem(key)).toBeNull();
  });
});
