import AsyncStorage from "@react-native-async-storage/async-storage";

const AUTH_TOKEN_KEY = "boran.ai.authToken";

export async function saveAuthToken(token: string): Promise<void> {
  const normalizedToken = token.trim();
  if (!normalizedToken) {
    throw new Error("Access token bos oldugu icin kaydedilemedi.");
  }
  await AsyncStorage.setItem(AUTH_TOKEN_KEY, normalizedToken);
  const persistedToken = await AsyncStorage.getItem(AUTH_TOKEN_KEY);
  const isSaved = (persistedToken?.trim() ?? "") === normalizedToken;
  console.log("[auth-storage] token saved:", {
    hasToken: true,
    tokenPrefix: normalizedToken.slice(0, 12),
    persisted: isSaved,
  });
  if (!isSaved) {
    throw new Error("Access token AsyncStorage'a kaydedilemedi.");
  }
}

export async function getAuthToken(): Promise<string | null> {
  const token = await AsyncStorage.getItem(AUTH_TOKEN_KEY);
  const normalizedToken = token?.trim() ?? "";
  console.log("[auth-storage] token loaded:", {
    hasToken: Boolean(normalizedToken),
    tokenPrefix: normalizedToken.slice(0, 12),
  });
  return normalizedToken || null;
}

export async function clearAuthToken(): Promise<void> {
  await AsyncStorage.removeItem(AUTH_TOKEN_KEY);
  console.log("[auth-storage] token cleared");
}
