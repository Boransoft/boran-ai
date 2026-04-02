type Props = {
  role: "user" | "assistant";
  content: string;
};

export default function ChatMessageBubble({ role, content }: Props) {
  return (
    <article className={`bubble ${role === "user" ? "bubble-user" : "bubble-ai"}`}>
      <p className="bubble-role">{role === "user" ? "You" : "boran.ai"}</p>
      <p className="bubble-content">{content}</p>
    </article>
  );
}
