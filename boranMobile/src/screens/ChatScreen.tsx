import React, { useMemo, useRef, useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { errorCodes, isErrorWithCode, keepLocalCopy, pick, types } from "@react-native-documents/picker";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";

import { ChatBubble } from "../components/ChatBubble";
import { Composer } from "../components/Composer";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import { sendChatMessage } from "../services/chatService";
import { uploadDocument } from "../services/documentService";
import { chatWithVoice } from "../services/voiceService";
import { theme } from "../utils/theme";
import { ChatMessage } from "../utils/types";

type ChatScreenProps = {
  token: string;
  onLogout: () => Promise<void>;
};

function createMessageId(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

function createMessage(type: ChatMessage["type"], text?: string, audioUrl?: string): ChatMessage {
  return {
    id: createMessageId(),
    type,
    text,
    audioUrl,
    createdAt: Date.now(),
  };
}

function extractAssistantReply(payload: any): string {
  if (!payload) return "";

  if (typeof payload === "string") return payload.trim();

  return (
    payload.reply ??
    payload.message ??
    payload.response ??
    payload.answer ??
    payload.text ??
    payload?.data?.reply ??
    payload?.data?.message ??
    payload?.data?.response ??
    payload?.data?.answer ??
    payload?.data?.text ??
    ""
  )
    .toString()
    .trim();
}

export function ChatScreen({ token, onLogout }: ChatScreenProps) {
  const insets = useSafeAreaInsets();
  const accessToken = token.trim();
  const [messages, setMessages] = useState<ChatMessage[]>([
    createMessage("system", "Tek ekran aktif. Chat, voice ve pdf yukleme hazir."),
  ]);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isVoiceLoading, setIsVoiceLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const { isRecording, startRecording, stopRecording } = useAudioRecorder();
  const listRef = useRef<FlatList<ChatMessage> | null>(null);

  const anyBusy = useMemo(() => isSending || isVoiceLoading || isUploading, [isSending, isVoiceLoading, isUploading]);

  const pushMessages = (next: ChatMessage[]) => {
    setMessages((prev) => {
      const merged = [...prev, ...next];
      setTimeout(() => {
        listRef.current?.scrollToEnd({ animated: true });
      }, 0);
      return merged;
    });
  };

  const pushSystemMessage = (text: string) => {
    pushMessages([createMessage("system", text)]);
  };

  const ensureSession = async (): Promise<boolean> => {
    const hasToken = accessToken.length > 0;
    console.log("[chat-screen] token:", hasToken ? "present" : "missing");
    if (hasToken) {
      return true;
    }
    pushSystemMessage("Oturum süresi doldu, tekrar giriş yap.");
    await onLogout();
    return false;
  };

  const handleSendText = async () => {
    const text = inputText.trim();
    if (!text || anyBusy || isRecording) {
      return;
    }
    if (!(await ensureSession())) {
      return;
    }

    setInputText("");
    pushMessages([createMessage("user_text", text)]);

    try {
      setIsSending(true);

      const response = await sendChatMessage({
        token: accessToken,
        message: text,
      });

      const assistantReply = extractAssistantReply(response);

      if (!assistantReply) {
        console.log("Chat response payload:", response);
        throw new Error("Backend yanit verdi ama cevap metni bulunamadi.");
      }

      pushMessages([createMessage("assistant_text", assistantReply)]);
    } catch (error: any) {
      console.log("Text chat error:", error?.response?.data ?? error?.message ?? error);
      const status = error?.response?.status;
      const detailText = String(error?.response?.data?.detail ?? error?.response?.data?.message ?? error?.message ?? "");
      if (status === 401 || detailText.includes("[401]") || detailText.includes("401")) {
        pushSystemMessage("Oturum süresi doldu, tekrar giriş yap.");
        await onLogout();
        return;
      }

      const detail =
        error?.response?.data?.detail ??
        error?.response?.data?.message ??
        error?.message;

      pushSystemMessage(typeof detail === "string" ? detail : "Text chat istegi basarisiz oldu.");
    } finally {
      setIsSending(false);
    }
  };

  const handleVoicePress = async () => {
    if (isSending || isUploading) {
      return;
    }
    if (!(await ensureSession())) {
      return;
    }

    if (!isRecording) {
      try {
        await startRecording();
      } catch (error: any) {
        pushSystemMessage(error?.message ?? "Kayit baslatilamadi.");
      }
      return;
    }

    try {
      setIsVoiceLoading(true);
      const recordPath = await stopRecording();
      const response = await chatWithVoice({
        token: accessToken,
        audioPath: recordPath,
      });

      const next: ChatMessage[] = [
        createMessage("user_voice_transcript", response.transcript),
        createMessage("assistant_text", response.reply),
      ];

      if (response.audio_url) {
        next.push(createMessage("assistant_audio", "Sesli cevap hazir.", response.audio_url));
      }

      if (response.warning) {
        next.push(createMessage("system", response.warning));
      }

      pushMessages(next);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      pushSystemMessage(typeof detail === "string" ? detail : "Voice chat istegi basarisiz oldu.");
    } finally {
      setIsVoiceLoading(false);
    }
  };

  const handleUploadPress = async () => {
    if (anyBusy || isRecording) {
      return;
    }
    if (!(await ensureSession())) {
      return;
    }

    try {
      const [picked] = await pick({
        type: [types.pdf],
      });

      const pickedName = picked.name ?? `document-${Date.now()}.pdf`;
      const copied = await keepLocalCopy({
        destination: "cachesDirectory",
        files: [{ uri: picked.uri, fileName: pickedName }],
      });

      const localCopy = copied[0];
      const uri = localCopy.status === "success" ? localCopy.localUri : picked.uri;

      if (!uri) {
        throw new Error("PDF dosyasi secilemedi.");
      }

      setIsUploading(true);

      await uploadDocument({
        token: accessToken,
        file: {
          uri,
          name: pickedName,
          type: picked.type ?? "application/pdf",
        },
        category: "general",
      });

      pushSystemMessage("Belge yuklendi ve ogrenme pipeline'ina gonderildi.");
    } catch (error: any) {
      if (isErrorWithCode(error) && error.code === errorCodes.OPERATION_CANCELED) {
        return;
      }

      const detail = error?.response?.data?.detail;
      pushSystemMessage(typeof detail === "string" ? detail : "Belge yukleme basarisiz oldu.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <KeyboardAvoidingView
        style={styles.keyboardContainer}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={0}
      >
        <View style={styles.header}>
          <Text style={styles.title}>boran.ai</Text>
          <Pressable style={styles.logoutButton} onPress={onLogout}>
            <Text style={styles.logoutText}>Logout</Text>
          </Pressable>
        </View>

        <View style={styles.chatArea}>
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(item) => item.id}
            style={styles.list}
            contentContainerStyle={styles.listContent}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"}
            renderItem={({ item }) => <ChatBubble message={item} token={accessToken} />}
          />
        </View>

        <Composer
          value={inputText}
          onChangeText={setInputText}
          onSend={handleSendText}
          onVoicePress={handleVoicePress}
          onUploadPress={handleUploadPress}
          isRecording={isRecording}
          isSending={isSending}
          isVoiceLoading={isVoiceLoading}
          isUploading={isUploading}
          bottomInset={Math.max(insets.bottom, 8)}
        />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  keyboardContainer: {
    flex: 1,
  },
  header: {
    minHeight: 50,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: theme.colors.surface,
  },
  title: {
    color: theme.colors.text,
    fontSize: 20,
    fontWeight: "700",
  },
  logoutButton: {
    minHeight: 32,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 10,
  },
  logoutText: {
    color: theme.colors.mutedText,
    fontSize: 11,
    fontWeight: "700",
  },
  chatArea: {
    flex: 1,
  },
  list: {
    flex: 1,
  },
  listContent: {
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 6,
  },
});
