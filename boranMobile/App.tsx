import React, { useEffect, useState } from "react";
import { ActivityIndicator, StatusBar, StyleSheet, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { LoginScreen } from "./src/screens/LoginScreen";
import { MainScreen } from "./src/screens/MainScreen";
import { getStoredValidToken } from "./src/services/authService";
import { setAuthFailureHandler, syncApiBaseUrlFromStorage } from "./src/services/api";
import { clearAuthToken, saveAuthToken } from "./src/utils/storage";
import { theme } from "./src/utils/theme";

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [isBooting, setIsBooting] = useState(true);
  const normalizedToken = token?.trim() ?? null;

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const [existingToken] = await Promise.all([
          getStoredValidToken(),
          syncApiBaseUrlFromStorage(),
        ]);
        console.log("[app] bootstrap token:", {
          hasToken: Boolean(existingToken),
          tokenPrefix: (existingToken ?? "").slice(0, 12),
        });
        setToken(existingToken);
      } finally {
        setIsBooting(false);
      }
    };

    void bootstrap();
  }, []);

  useEffect(() => {
    setAuthFailureHandler(async () => {
      await clearAuthToken();
      setToken(null);
    });

    return () => {
      setAuthFailureHandler(null);
    };
  }, []);

  const handleLogin = async (nextToken: string) => {
    const safeToken = nextToken.trim();
    if (!safeToken) {
      throw new Error("Login sonrasi access_token bos geldi.");
    }
    console.log("[app] handleLogin token:", {
      hasToken: Boolean(safeToken),
      tokenPrefix: safeToken.slice(0, 12),
    });
    await saveAuthToken(safeToken);
    setToken(safeToken);
  };

  const handleLogout = async () => {
    await clearAuthToken();
    setToken(null);
  };

  if (isBooting) {
    return (
      <SafeAreaProvider>
        <View style={styles.bootContainer}>
          <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />
        {normalizedToken ? <MainScreen token={normalizedToken} onLogout={handleLogout} /> : <LoginScreen onLogin={handleLogin} />}
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  bootContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.colors.background,
  },
});
