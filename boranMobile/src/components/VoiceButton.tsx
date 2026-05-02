import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";

import { theme } from "../utils/theme";

type VoiceButtonProps = {
  isRecording: boolean;
  isBusy?: boolean;
  onPress: () => void;
  disabled?: boolean;
};

export function VoiceButton({ isRecording, isBusy = false, onPress, disabled = false }: VoiceButtonProps) {
  const label = isRecording ? "STOP" : "MIC";
  const busy = isBusy && !isRecording;

  return (
    <Pressable
      style={[styles.button, isRecording ? styles.recording : undefined, disabled ? styles.disabled : undefined]}
      onPress={onPress}
      disabled={disabled}
    >
      {busy ? <ActivityIndicator size="small" color={theme.colors.text} /> : <Text style={styles.label}>{label}</Text>}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    height: 44,
    minWidth: 46,
    paddingHorizontal: 10,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.colors.primary,
    flexShrink: 0,
  },
  recording: {
    backgroundColor: theme.colors.danger,
  },
  disabled: {
    opacity: 0.5,
  },
  label: {
    color: theme.colors.text,
    fontWeight: "700",
    fontSize: 12,
    letterSpacing: 0.2,
  },
});
