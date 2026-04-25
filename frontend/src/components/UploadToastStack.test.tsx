// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { UploadToastItem } from "./UploadToastStack";
import UploadToastStack from "./UploadToastStack";

function makeToast(overrides?: Partial<UploadToastItem>): UploadToastItem {
  return {
    id: "t1",
    fileId: "f1",
    fileName: "doc.pdf",
    status: "queued",
    message: "Dosya kuyruga alindi",
    updatedAt: Date.now(),
    autoDismissMs: null,
    dismissible: false,
    ...overrides,
  };
}

describe("UploadToastStack", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("auto dismisses success toast after 3 seconds", () => {
    const onDismiss = vi.fn();
    render(
      <UploadToastStack
        toasts={[
          makeToast({
            id: "s1",
            status: "success",
            message: "Belge basariyla yuklendi",
            autoDismissMs: 3000,
          }),
        ]}
        onDismiss={onDismiss}
      />,
    );

    vi.advanceTimersByTime(2999);
    expect(onDismiss).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onDismiss).toHaveBeenCalledWith("f1", "success");
  });

  it("keeps error toast visible and allows manual dismiss", () => {
    const onDismiss = vi.fn();
    render(
      <UploadToastStack
        toasts={[
          makeToast({
            id: "e1",
            status: "error",
            message: "Belge yuklenemedi",
            dismissible: true,
          }),
        ]}
        onDismiss={onDismiss}
      />,
    );

    vi.advanceTimersByTime(10_000);
    expect(onDismiss).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "doc.pdf bildirimini kapat" }));
    expect(onDismiss).toHaveBeenCalledWith("f1", "error");
  });

  it("renders multi-upload stack", () => {
    render(
      <UploadToastStack
        toasts={[
          makeToast({ id: "t1", fileId: "f1", fileName: "a.pdf", status: "uploading", message: "Dosya yukleniyor..." }),
          makeToast({ id: "t2", fileId: "f2", fileName: "b.pdf", status: "processing", message: "Belge isleniyor..." }),
        ]}
        onDismiss={vi.fn()}
      />,
    );

    expect(screen.getByText("Dosya yukleniyor...")).toBeTruthy();
    expect(screen.getByText("Belge isleniyor...")).toBeTruthy();
  });
});

