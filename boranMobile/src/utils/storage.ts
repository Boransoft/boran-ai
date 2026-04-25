import AsyncStorage from "@react-native-async-storage/async-storage";

const AUTH_TOKEN_KEY = "boran.ai.authToken";

export async function saveAuthToken(token: string): Promise<void> {
  await AsyncStorage.setItem(AUTH_TOKEN_KEY, token);
}

export async function getAuthToken(): Promise<string | null> {
  return AsyncStorage.getItem(AUTH_TOKEN_KEY);
}

export async function clearAuthToken(): Promise<void> {
  await AsyncStorage.removeItem(AUTH_TOKEN_KEY);
}
