// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { AppMessage } from "../types/message";
import MessageBubble from "./MessageBubble";

function assistantMessage(overrides?: Partial<AppMessage>): AppMessage {
  return {
    id: "m1",
    type: "assistant_text",
    content: "Merhaba",
    createdAt: Date.now(),
    status: "done",
    ...overrides,
  };
}

describe("MessageBubble citations", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders source list for assistant messages when citations exist", () => {
    render(
      <MessageBubble
        message={assistantMessage({
          meta: {
            sources: [
              { file_name: "Mubeccerat.pdf", source_id: "src_1" },
              { file_name: "celcelutiyyeden.pdf", source_id: "src_2" },
            ],
          },
        })}
      />,
    );

    expect(screen.getByText("Kaynaklar")).toBeTruthy();
    expect(screen.getByText("Mubeccerat.pdf")).toBeTruthy();
    expect(screen.getByText("celcelutiyyeden.pdf")).toBeTruthy();
  });

  it("does not render citation area when assistant message has no sources", () => {
    render(<MessageBubble message={assistantMessage()} />);

    expect(screen.queryByText("Kaynak")).toBeNull();
    expect(screen.queryByText("Kaynaklar")).toBeNull();
  });

  it("ignores malformed sources safely", () => {
    render(
      <MessageBubble
        message={assistantMessage({
          meta: {
            sources: [null, { file_name: "" }, { unknown: "x" }],
          } as unknown as AppMessage["meta"],
        })}
      />,
    );

    expect(screen.queryByText("Kaynak")).toBeNull();
    expect(screen.queryByText("Kaynaklar")).toBeNull();
    expect(screen.getByText("Merhaba")).toBeTruthy();
  });
});
