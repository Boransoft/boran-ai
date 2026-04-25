import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { ChatMessage } from "../utils/types";
import { theme } from "../utils/theme";
import { AudioPlayer } from "./AudioPlayer";

type ChatBubbleProps = {
  message: ChatMessage;
  token: string;
};

export function ChatBubble({ message, token }: ChatBubbleProps) {
  const isUser = message.type === "user_text" || message.type === "user_voice_transcript";
  const isSystem = message.type === "system";
  const isAssistant = !isUser && !isSystem;

  return (
    <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
      <View
        style={[
          styles.bubble,
          isUser ? styles.userBubble : undefined,
          isAssistant ? styles.assistantBubble : undefined,
          isSystem ? styles.systemBubble : undefined,
        ]}
      >
        {message.text ? <Text style={styles.text}>{message.text}</Text> : null}
        {message.type === "assistant_audio" && message.audioUrl ? <AudioPlayer token={token} audioUrl={message.audioUrl} /> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    width: "100%",
    marginBottom: 10,
  },
  rowUser: {
    alignItems: "flex-end",
  },
  rowAssistant: {
    alignItems: "flex-start",
  },
  bubble: {
    maxWidth: "88%",
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 9,
  },
  userBubble: {
    backgroundColor: theme.colors.userBubble,
  },
  assistantBubble: {
    backgroundColor: theme.colors.assistantBubble,
  },
  systemBubble: {
    backgroundColor: theme.colors.systemBubble,
    alignSelf: "center",
  },
  text: {
    color: theme.colors.text,
    fontSize: 15,
    lineHeight: 21,
  },
});
