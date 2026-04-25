import React, { useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { login } from "../services/authService";
import { getActiveApiBaseUrl, setActiveApiBaseUrl, syncApiBaseUrlFromStorage } from "../services/api";
import { getApiBaseUrl } from "../utils/env";
import { theme } from "../utils/theme";

type LoginScreenProps = {
  onLogin: (token: string) => Promise<void>;
};

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState(getApiBaseUrl());
  const [isLoading, setIsLoading] = useState(false);
  const [isSavingApi, setIsSavingApi] = useState(false);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [apiInfoText, setApiInfoText] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const loadApiAddress = async () => {
      const resolved = await syncApiBaseUrlFromStorage();
      if (mounted) {
        setApiBaseUrl(resolved);
      }
    };

    void loadApiAddress();

    return () => {
      mounted = false;
    };
  }, []);

  const handleSaveApiBaseUrl = async () => {
    try {
      setIsSavingApi(true);
      setErrorText(null);
      const saved = await setActiveApiBaseUrl(apiBaseUrl);
      setApiBaseUrl(saved);
      setApiInfoText(`Kaydedildi: ${saved}`);
    } catch (error: any) {
      const message = typeof error?.message === "string" ? error.message : "API adresi kaydedilemedi.";
      setErrorText(message);
      setApiInfoText(null);
    } finally {
      setIsSavingApi(false);
    }
  };

  const handleLogin = async () => {
    const cleanedEmail = email.trim();
    if (!cleanedEmail || !password) {
      setErrorText("Email ve sifre zorunlu.");
      return;
    }

    try {
      setIsLoading(true);
      setErrorText(null);
      const response = await login({
        email: cleanedEmail,
        password,
      });
      await onLogin(response.access_token);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      const isNetworkError = !error?.response;
      const fallback = typeof detail === "string"
        ? detail
        : isNetworkError
          ? `Sunucuya baglanilamadi: ${getActiveApiBaseUrl()}`
          : "Giris basarisiz oldu.";
      setErrorText(fallback);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <View style={styles.card}>
        <Text style={styles.title}>boran.ai</Text>
        <Text style={styles.subtitle}>Mobil giris</Text>

        <Text style={styles.apiLabel}>API adresi</Text>
        <View style={styles.apiRow}>
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            value={apiBaseUrl}
            onChangeText={setApiBaseUrl}
            placeholder="http://192.168.1.105:8000"
            placeholderTextColor={theme.colors.mutedText}
            style={[styles.input, styles.apiInput]}
            editable={!isLoading && !isSavingApi}
          />
          <Pressable
            style={[styles.saveButton, isSavingApi ? styles.disabled : undefined]}
            onPress={handleSaveApiBaseUrl}
            disabled={isLoading || isSavingApi}
          >
            {isSavingApi ? <ActivityIndicator size="small" color={theme.colors.text} /> : <Text style={styles.saveLabel}>KAYDET</Text>}
          </Pressable>
        </View>
        {apiInfoText ? <Text style={styles.apiInfo}>{apiInfoText}</Text> : null}

        <TextInput
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
          placeholder="email"
          placeholderTextColor={theme.colors.mutedText}
          style={styles.input}
          editable={!isLoading}
        />
        <TextInput
          secureTextEntry
          value={password}
          onChangeText={setPassword}
          placeholder="password"
          placeholderTextColor={theme.colors.mutedText}
          style={styles.input}
          editable={!isLoading}
        />

        <Pressable style={[styles.loginButton, isLoading ? styles.disabled : undefined]} onPress={handleLogin} disabled={isLoading}>
          {isLoading ? <ActivityIndicator size="small" color={theme.colors.text} /> : <Text style={styles.loginLabel}>LOGIN</Text>}
        </Pressable>

        {errorText ? <Text style={styles.error}>{errorText}</Text> : null}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
    justifyContent: "center",
    padding: 20,
  },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: 18,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    color: theme.colors.text,
  },
  subtitle: {
    marginTop: 4,
    marginBottom: 12,
    color: theme.colors.mutedText,
  },
  apiLabel: {
    color: theme.colors.mutedText,
    fontSize: 12,
    marginBottom: 6,
  },
  apiRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
  },
  input: {
    minHeight: 46,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: "#0b1118",
    color: theme.colors.text,
    paddingHorizontal: 12,
    marginBottom: 10,
  },
  apiInput: {
    flex: 1,
    marginBottom: 0,
    marginRight: 8,
  },
  saveButton: {
    minHeight: 46,
    minWidth: 84,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: "#0f172a",
    paddingHorizontal: 10,
  },
  saveLabel: {
    color: theme.colors.text,
    fontWeight: "700",
    fontSize: 12,
  },
  apiInfo: {
    marginTop: -4,
    marginBottom: 8,
    color: theme.colors.mutedText,
    fontSize: 12,
  },
  loginButton: {
    marginTop: 6,
    minHeight: 46,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.colors.primary,
  },
  disabled: {
    opacity: 0.6,
  },
  loginLabel: {
    color: theme.colors.text,
    fontWeight: "700",
    letterSpacing: 0.4,
  },
  error: {
    marginTop: 10,
    color: theme.colors.danger,
    fontSize: 13,
  },
});
