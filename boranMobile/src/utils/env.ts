import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";

const API_BASE_URL_KEY = "boran.ai.apiBaseUrl";
const DEVICE_BASE_URL = "http://192.168.1.105:8000";
const ANDROID_EMULATOR_BASE_URL = "http://10.0.2.2:8000";

function isAndroidEmulator(): boolean {
  if (Platform.OS !== "android") {
    return false;
  }

  const constants = Platform.constants as Record<string, unknown>;
  const fingerprint = String(constants.Fingerprint ?? "").toLowerCase();
  const model = String(constants.Model ?? "").toLowerCase();
  const brand = String(constants.Brand ?? "").toLowerCase();
  const device = String(constants.Device ?? "").toLowerCase();
  const product = String(constants.Product ?? "").toLowerCase();

  return (
    fingerprint.includes("generic") ||
    fingerprint.includes("emulator") ||
    model.includes("emulator") ||
    model.includes("android sdk built for x86") ||
    model.includes("sdk_gphone") ||
    (brand.startsWith("generic") && device.startsWith("generic")) ||
    product.includes("sdk") ||
    product.includes("emulator")
  );
}

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
  return isAndroidEmulator() ? ANDROID_EMULATOR_BASE_URL : DEVICE_BASE_URL;
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
