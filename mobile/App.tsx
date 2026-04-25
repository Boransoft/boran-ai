import React, { useEffect, useState } from "react";
import { ActivityIndicator, StatusBar, StyleSheet, View } from "react-native";

import { LoginScreen } from "./src/screens/LoginScreen";
import { MainScreen } from "./src/screens/MainScreen";
import { clearAuthToken, getAuthToken, saveAuthToken } from "./src/utils/storage";
import { theme } from "./src/utils/theme";

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [isBooting, setIsBooting] = useState(true);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const existingToken = await getAuthToken();
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
      <View style={styles.bootContainer}>
        <StatusBar barStyle="light-content" />
        <ActivityIndicator size="large" color={theme.colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      {token ? <MainScreen token={token} onLogout={handleLogout} /> : <LoginScreen onLogin={handleLogin} />}
    </View>
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
