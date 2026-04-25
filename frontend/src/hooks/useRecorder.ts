import { useCallback, useMemo, useRef, useState } from "react";

type RecorderState = {
  isRecording: boolean;
  mimeType: string;
  isSupported: boolean;
  supportMessage: string;
  error: string;
  requestPermission: () => Promise<boolean>;
  startRecording: () => Promise<boolean>;
  stopRecording: () => Promise<Blob | null>;
};

const mimeCandidates = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
  "audio/ogg",
  "audio/wav",
];

function detectMimeType(): string {
  if (typeof MediaRecorder === "undefined") {
    return "";
  }

  for (const candidate of mimeCandidates) {
    if (MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }

  return "";
}

export function useRecorder(): RecorderState {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState("");

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const stopResolverRef = useRef<((value: Blob | null) => void) | null>(null);

  const mimeType = useMemo(detectMimeType, []);
  const isSupported = useMemo(
    () => typeof window !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined",
    [],
  );

  const supportMessage = isSupported
    ? "ok"
    : "Bu tarayıcı mikrofon kaydı için gerekli MediaRecorder API desteğini sağlamıyor.";

  const cleanup = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    recorderRef.current = null;
    setIsRecording(false);
  }, []);

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!isSupported) {
      setError(supportMessage);
      return false;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setError("");
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mikrofon izni alınamadı.");
      return false;
    }
  }, [isSupported, supportMessage]);

  const startRecording = useCallback(async (): Promise<boolean> => {
    setError("");
    chunksRef.current = [];

    if (!isSupported) {
      setError(supportMessage);
      return false;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onerror = () => {
        setError("Ses kaydı sırasında beklenmeyen bir hata oluştu.");
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || "audio/webm" });
        const resolver = stopResolverRef.current;
        stopResolverRef.current = null;
        cleanup();
        resolver?.(blob.size > 0 ? blob : null);
      };

      recorder.start();
      recorderRef.current = recorder;
      setIsRecording(true);
      return true;
    } catch (err) {
      cleanup();
      setError(err instanceof Error ? err.message : "Kayıt başlatılamadı.");
      return false;
    }
  }, [cleanup, isSupported, mimeType, supportMessage]);

  const stopRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder) {
        resolve(null);
        return;
      }

      stopResolverRef.current = resolve;
      if (recorder.state !== "inactive") {
        recorder.stop();
      } else {
        cleanup();
        resolve(null);
      }
    });
  }, [cleanup]);

  return {
    isRecording,
    mimeType,
    isSupported,
    supportMessage,
    error,
    requestPermission,
    startRecording,
    stopRecording,
  };
}
