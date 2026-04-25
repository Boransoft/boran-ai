import { useEffect, useState } from "react";
import { PermissionsAndroid, Platform } from "react-native";
import AudioRecord from "react-native-audio-record";

type RecorderHook = {
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<string>;
};

async function ensureRecordPermission(): Promise<void> {
  if (Platform.OS !== "android") {
    return;
  }
  const granted = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.RECORD_AUDIO, {
    title: "Mikrofon izni",
    message: "Sesli sohbet icin mikrofon erisimi gerekiyor.",
    buttonPositive: "Tamam",
  });
  if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
    throw new Error("Mikrofon izni verilmedi.");
  }
}

export function useAudioRecorder(): RecorderHook {
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    AudioRecord.init({
      sampleRate: 16000,
      channels: 1,
      bitsPerSample: 16,
      wavFile: "boran-ai-record.wav",
      audioSource: 6,
    });
  }, []);

  const startRecording = async () => {
    await ensureRecordPermission();
    await AudioRecord.start();
    setIsRecording(true);
  };

  const stopRecording = async (): Promise<string> => {
    try {
      const path = await AudioRecord.stop();
      return path;
    } finally {
      setIsRecording(false);
    }
  };

  return {
    isRecording,
    startRecording,
    stopRecording,
  };
}
