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
    height: 52,
    minWidth: 52,
    paddingHorizontal: 12,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.colors.primary,
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
    letterSpacing: 0.6,
  },
});
