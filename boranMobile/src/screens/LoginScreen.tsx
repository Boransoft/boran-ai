import React, { useEffect, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { login, register } from "../services/authService";
import { getActiveApiBaseUrl, setActiveApiBaseUrl, syncApiBaseUrlFromStorage } from "../services/api";
import { getApiBaseUrl } from "../utils/env";
import { theme } from "../utils/theme";

type LoginScreenProps = {
  onLogin: (token: string) => Promise<void>;
};

type AuthMode = "login" | "register";

const MIN_PASSWORD_LENGTH = 8;

function extractDetailText(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((item) => extractDetailText(item)).filter(Boolean).join(" ");
  }

  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    if (typeof record.msg === "string") {
      return record.msg;
    }
    if (typeof record.message === "string") {
      return record.message;
    }
    if (typeof record.detail === "string") {
      return record.detail;
    }
  }

  return "";
}

function isUserExistsError(status: number | undefined, text: string): boolean {
  if (status === 409) {
    return true;
  }
  return /(already|exists|duplicate|taken|in use|kullanilmaktadir|mevcut|kayıtlı)/i.test(text);
}

function isShortPasswordError(status: number | undefined, text: string): boolean {
  if (status === 422) {
    return /(min|least|length|short|8|sekiz)/i.test(text);
  }
  return /(too short|min|least|length|8|sekiz|kisa)/i.test(text);
}

function isInvalidCredentialError(status: number | undefined, text: string): boolean {
  if (status === 401 || status === 403) {
    return true;
  }
  return /(invalid|incorrect|wrong|credentials|unauthorized|gecersiz|hatali)/i.test(text);
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
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

  const handleAuthSubmit = async () => {
    const cleanedUsername = username.trim();
    const cleanedDisplayName = displayName.trim();
    const cleanedEmail = email.trim();

    if (mode === "register" && (!cleanedUsername || !cleanedDisplayName || !cleanedEmail || !password)) {
      setErrorText("Kullanici adi, gorunen ad, email ve sifre zorunlu.");
      return;
    }

    if (mode === "login" && (!cleanedEmail || !password)) {
      setErrorText("Email ve sifre zorunlu.");
      return;
    }

    if (password.length < MIN_PASSWORD_LENGTH) {
      setErrorText("Sifre en az 8 karakter olmali.");
      return;
    }

    try {
      setIsLoading(true);
      setErrorText(null);

      const response = mode === "register"
        ? await register({
          username: cleanedUsername,
          displayName: cleanedDisplayName,
          email: cleanedEmail,
          password,
        })
        : await login({
          email: cleanedEmail,
          password,
        });

      const accessToken = typeof response.access_token === "string" ? response.access_token.trim() : "";
      console.log("[login-screen] access_token:", accessToken ? "present" : "missing");
      if (!accessToken) {
        setErrorText("Giris basarisiz oldu: token alinamadi.");
        return;
      }
      await onLogin(accessToken);
    } catch (error: any) {
      const status = error?.response?.status as number | undefined;
      const detailText = extractDetailText(error?.response?.data?.detail ?? error?.response?.data?.message ?? error?.message);
      const isNetworkError = !error?.response;

      if (isNetworkError) {
        setErrorText(`Sunucuya ulasilamadi: ${getActiveApiBaseUrl()}`);
      } else if (mode === "register" && isUserExistsError(status, detailText)) {
        setErrorText("Bu kullanici adi veya email zaten kayitli.");
      } else if (isShortPasswordError(status, detailText)) {
        setErrorText("Sifre en az 8 karakter olmali.");
      } else if (mode === "login" && isInvalidCredentialError(status, detailText)) {
        setErrorText("Gecersiz kullanici veya sifre.");
      } else if (detailText) {
        setErrorText(detailText);
      } else {
        setErrorText(mode === "register" ? "Kayit islemi basarisiz oldu." : "Giris basarisiz oldu.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <View style={styles.card}>
        <Text style={styles.title}>boran.ai</Text>
        <Text style={styles.subtitle}>{mode === "register" ? "Mobil kayit" : "Mobil giris"}</Text>

        <View style={styles.modeRow}>
          <Pressable
            style={[styles.modeButton, mode === "login" ? styles.modeButtonActive : undefined]}
            onPress={() => {
              setMode("login");
              setErrorText(null);
            }}
            disabled={isLoading}
          >
            <Text style={[styles.modeLabel, mode === "login" ? styles.modeLabelActive : undefined]}>GIRIS YAP</Text>
          </Pressable>
          <Pressable
            style={[styles.modeButton, mode === "register" ? styles.modeButtonActive : undefined]}
            onPress={() => {
              setMode("register");
              setErrorText(null);
            }}
            disabled={isLoading}
          >
            <Text style={[styles.modeLabel, mode === "register" ? styles.modeLabelActive : undefined]}>HESAP OLUSTUR</Text>
          </Pressable>
        </View>

        <Text style={styles.apiLabel}>API adresi</Text>
        <View style={styles.apiRow}>
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            value={apiBaseUrl}
            onChangeText={setApiBaseUrl}
            placeholder="https://boran-ai.onrender.com"
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

        {mode === "register" ? (
          <>
            <TextInput
              autoCapitalize="none"
              value={username}
              onChangeText={setUsername}
              placeholder="username"
              placeholderTextColor={theme.colors.mutedText}
              style={styles.input}
              editable={!isLoading}
            />
            <TextInput
              value={displayName}
              onChangeText={setDisplayName}
              placeholder="display_name"
              placeholderTextColor={theme.colors.mutedText}
              style={styles.input}
              editable={!isLoading}
            />
          </>
        ) : null}

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

        <Pressable style={[styles.loginButton, isLoading ? styles.disabled : undefined]} onPress={handleAuthSubmit} disabled={isLoading}>
          {isLoading
            ? <ActivityIndicator size="small" color={theme.colors.text} />
            : <Text style={styles.loginLabel}>{mode === "register" ? "KAYIT OL" : "LOGIN"}</Text>}
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
    marginBottom: 10,
    color: theme.colors.mutedText,
  },
  modeRow: {
    flexDirection: "row",
    marginBottom: 10,
    gap: 8,
  },
  modeButton: {
    flex: 1,
    minHeight: 38,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: "#0b1118",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 8,
  },
  modeButtonActive: {
    backgroundColor: "#111a27",
    borderColor: theme.colors.primary,
  },
  modeLabel: {
    color: theme.colors.mutedText,
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
  modeLabelActive: {
    color: theme.colors.text,
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
