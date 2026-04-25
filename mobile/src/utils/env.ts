import { Platform } from "react-native";

const DEVICE_BASE_URL = "http://192.168.1.34:8000";
const ANDROID_EMULATOR_BASE_URL = "http://10.0.2.2:8000";

// Emulatorde gelistirme icin true, fiziksel cihazda false yapin.
const USE_ANDROID_EMULATOR = true;

export function getApiBaseUrl(): string {
  if (Platform.OS === "android" && USE_ANDROID_EMULATOR) {
    return ANDROID_EMULATOR_BASE_URL;
  }
  return DEVICE_BASE_URL;
}
