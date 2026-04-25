import { useEffect, useRef } from "react";

import type { AppMessage } from "../types/message";
import MessageBubble from "./MessageBubble";

type MessageListProps = {
  messages: AppMessage[];
  onAudioPlay?: () => void;
  onAudioEnded?: () => void;
};

export default function MessageList({ messages, onAudioPlay, onAudioEnded }: MessageListProps) {
  const containerRef = useRef<HTMLElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const shouldAutoScrollRef = useRef(true);
  const hasAutoScrolledOnceRef = useRef(false);

  const updateAutoScrollPreference = () => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    shouldAutoScrollRef.current = distanceFromBottom <= 96;
  };

  useEffect(() => {
    updateAutoScrollPreference();
  }, []);

  useEffect(() => {
    if (!shouldAutoScrollRef.current) {
      return;
    }
    bottomRef.current?.scrollIntoView({ behavior: hasAutoScrolledOnceRef.current ? "smooth" : "auto", block: "end" });
    hasAutoScrolledOnceRef.current = true;
  }, [messages]);

  return (
    <section
      ref={containerRef}
      onScroll={updateAutoScrollPreference}
      className="min-h-0 flex-1 overflow-y-auto px-2.5 pb-2 pt-2 overscroll-contain sm:px-4"
    >
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-3 sm:gap-3.5">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} onAudioPlay={onAudioPlay} onAudioEnded={onAudioEnded} />
        ))}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
