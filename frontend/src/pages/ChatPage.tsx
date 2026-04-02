import { FormEvent, useMemo, useState } from "react";

import ChatMessageBubble from "../components/ChatMessageBubble";
import { useAuthGuard } from "../hooks/useAuthGuard";
import { sendChatMessage } from "../services/chatService";
import { useAuthStore } from "../store/authStore";
import { useSettingsStore } from "../store/settingsStore";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export default function ChatPage() {
  useAuthGuard();

  const token = useAuthStore((state) => state.token);
  const includeReflectionContext = useSettingsStore((state) => state.includeReflectionContext);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!token || !canSend) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user" as const,
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError("");

    try {
      const response = await sendChatMessage({
        token,
        message: userMessage.content,
        includeReflectionContext,
      });

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.reply,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-content">
      <div className="messages">
        {messages.length === 0 ? <p className="muted">Start a conversation.</p> : null}
        {messages.map((msg) => (
          <ChatMessageBubble key={msg.id} role={msg.role} content={msg.content} />
        ))}
      </div>

      {error ? <p className="error-text">{error}</p> : null}

      <form className="composer" onSubmit={onSubmit}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          rows={3}
        />
        <button className="primary" disabled={!canSend} type="submit">
          {loading ? "Sending..." : "Send"}
        </button>
      </form>
    </section>
  );
}
