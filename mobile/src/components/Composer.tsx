import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { theme } from "../utils/theme";
import { UploadButton } from "./UploadButton";
import { VoiceButton } from "./VoiceButton";

type ComposerProps = {
  value: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  onVoicePress: () => void;
  onUploadPress: () => void;
  isRecording: boolean;
  isSending: boolean;
  isVoiceLoading: boolean;
  isUploading: boolean;
};

export function Composer({
  value,
  onChangeText,
  onSend,
  onVoicePress,
  onUploadPress,
  isRecording,
  isSending,
  isVoiceLoading,
  isUploading,
}: ComposerProps) {
  const busy = isSending || isVoiceLoading || isUploading;
  const canSend = value.trim().length > 0 && !busy;

  return (
    <View style={styles.container}>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        style={styles.input}
        placeholder="Mesajinizi yazin..."
        placeholderTextColor={theme.colors.mutedText}
        editable={!busy}
      />
      <VoiceButton isRecording={isRecording} isBusy={isVoiceLoading} onPress={onVoicePress} disabled={isSending || isUploading} />
      <UploadButton isLoading={isUploading} onPress={onUploadPress} disabled={isSending || isVoiceLoading || isRecording} />
      <Pressable style={[styles.sendButton, !canSend ? styles.sendDisabled : undefined]} onPress={onSend} disabled={!canSend}>
        {isSending ? <ActivityIndicator size="small" color={theme.colors.text} /> : <Text style={styles.sendLabel}>GONDER</Text>}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
    backgroundColor: theme.colors.background,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 110,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
    color: theme.colors.text,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  sendButton: {
    minHeight: 44,
    minWidth: 80,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.colors.primary,
    paddingHorizontal: 12,
  },
  sendDisabled: {
    opacity: 0.45,
  },
  sendLabel: {
    color: theme.colors.text,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
});
