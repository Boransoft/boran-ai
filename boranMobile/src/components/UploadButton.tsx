import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";

import { theme } from "../utils/theme";

type UploadButtonProps = {
  isLoading?: boolean;
  onPress: () => void;
  disabled?: boolean;
};

export function UploadButton({ isLoading = false, onPress, disabled = false }: UploadButtonProps) {
  return (
    <Pressable style={[styles.button, disabled ? styles.disabled : undefined]} onPress={onPress} disabled={disabled}>
      {isLoading ? <ActivityIndicator size="small" color={theme.colors.text} /> : <Text style={styles.label}>PDF</Text>}
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
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
    flexShrink: 0,
  },
  disabled: {
    opacity: 0.55,
  },
  label: {
    color: theme.colors.text,
    fontWeight: "700",
    letterSpacing: 0.3,
  },
});
