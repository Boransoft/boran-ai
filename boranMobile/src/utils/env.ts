import AsyncStorage from "@react-native-async-storage/async-storage";

const API_BASE_URL_KEY = "boran.ai.apiBaseUrl";
const DEFAULT_API_BASE_URL = "https://boran-ai.onrender.com";

function normalizeApiBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

function ensureValidApiBaseUrl(value: string): string {
  const normalized = normalizeApiBaseUrl(value);
  if (!normalized) {
    throw new Error("API adresi bos olamaz.");
  }
  if (!/^https?:\/\//i.test(normalized)) {
    throw new Error("API adresi http:// veya https:// ile baslamali.");
  }
  return normalized;
}

export function getApiBaseUrl(): string {
  return DEFAULT_API_BASE_URL;
}

export async function getStoredApiBaseUrl(): Promise<string | null> {
  const stored = await AsyncStorage.getItem(API_BASE_URL_KEY);
  if (!stored) {
    return null;
  }

  const normalized = normalizeApiBaseUrl(stored);
  if (!normalized) {
    await AsyncStorage.removeItem(API_BASE_URL_KEY);
    return null;
  }

  if (normalized !== stored) {
    await AsyncStorage.setItem(API_BASE_URL_KEY, normalized);
  }

  return normalized;
}

export async function resolveApiBaseUrl(): Promise<string> {
  return (await getStoredApiBaseUrl()) ?? getApiBaseUrl();
}

export async function saveApiBaseUrl(baseUrl: string): Promise<string> {
  const normalized = ensureValidApiBaseUrl(baseUrl);
  await AsyncStorage.setItem(API_BASE_URL_KEY, normalized);
  return normalized;
}
