import React, { useEffect, useState } from "react";
import { ActivityIndicator, StatusBar, StyleSheet, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { LoginScreen } from "./src/screens/LoginScreen";
import { MainScreen } from "./src/screens/MainScreen";
import { syncApiBaseUrlFromStorage } from "./src/services/api";
import { clearAuthToken, getAuthToken, saveAuthToken } from "./src/utils/storage";
import { theme } from "./src/utils/theme";

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [isBooting, setIsBooting] = useState(true);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const [existingToken] = await Promise.all([
          getAuthToken(),
          syncApiBaseUrlFromStorage(),
        ]);
        setToken(existingToken);
      } finally {
        setIsBooting(false);
      }
    };

    void bootstrap();
  }, []);

  const handleLogin = async (nextToken: string) => {
    await saveAuthToken(nextToken);
    setToken(nextToken);
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
        {token ? <MainScreen token={token} onLogout={handleLogout} /> : <LoginScreen onLogin={handleLogin} />}
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
