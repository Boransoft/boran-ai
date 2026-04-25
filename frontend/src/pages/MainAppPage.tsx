import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import Composer from "../components/Composer";
import MessageList from "../components/MessageList";
import StatusIndicator from "../components/StatusIndicator";
import TopBar from "../components/TopBar";
import UploadToastStack, { type UploadToastItem } from "../components/UploadToastStack";
import { MAX_UPLOAD_FILE_SIZE_BYTES, MAX_UPLOAD_SIZE_MB } from "../config/upload";
import { useRecorder } from "../hooks/useRecorder";
import { sendChatMessage } from "../services/chatService";
import type { ChatCitation, ChatResponse } from "../services/chatService";
import { uploadDocument } from "../services/documentService";
import { chatWithVoice, getAudioObjectUrl } from "../services/voiceService";
import { useAppStore } from "../store/appStore";
import { useAuthStore } from "../store/authStore";
import { useMessageStore } from "../store/messageStore";
import {
  CLEAR_PERSISTED_MESSAGES_ON_LOGOUT_DEFAULT,
  clearSessionCacheForUser,
  readJsonFromStorage,
  scheduleSessionCacheForUser,
  sessionStorageKey,
} from "../store/persistence";
import { useUploadStore } from "../store/uploadStore";
import { useVoiceStore } from "../store/voiceStore";
import type { ChatContextHint, UploadedDocument } from "../types/context";
import type { AppMessage, MessageSource } from "../types/message";
import type { UploadFileState } from "../types/upload";
import type { VoiceStatus } from "../types/voice";
import { createId } from "../utils/id";
import {
  queueSummary,
  retrievalNoHit,
  oversizedFile,
  SystemMessages,
  uploadSummary,
} from "../utils/systemMessages";

const UPLOAD_CONCURRENCY_LIMIT = 3;
const SUCCESS_TOAST_AUTO_DISMISS_MS = 3_000;
const ALLOWED_UPLOAD_EXTENSIONS = new Set(["pdf", "txt", "md", "docx", "png", "jpg", "jpeg", "webp"]);

const DOC_INTENT_PATTERN = /(pdf|belge|dokuman|dosya|kaynak|ozet|soru|cevap|icerik|ogrenme)/i;

type SystemStatus = "idle" | "loading" | "success" | "error";
type PersistedSession = {
  version: 1;
  draftText: string;
  systemStatus: SystemStatus;
  systemMessage: string;
  voiceStatus: VoiceStatus;
  voiceProvider: string;
  voiceError: string;
  updatedAt: number;
};

type UploadTask = {
  state: UploadFileState;
  file: File;
};

function uploadToastSignature(fileId: string, status: UploadFileState["status"]): string {
  return `${fileId}:${status}`;
}

function uploadToastBehavior(status: UploadFileState["status"]): { autoDismissMs: number | null; dismissible: boolean } {
  if (status === "success") {
    return { autoDismissMs: SUCCESS_TOAST_AUTO_DISMISS_MS, dismissible: false };
  }
  if (status === "error") {
    return { autoDismissMs: null, dismissible: true };
  }
  return { autoDismissMs: null, dismissible: false };
}

function isSystemStatus(value: unknown): value is SystemStatus {
  return value === "idle" || value === "loading" || value === "success" || value === "error";
}

function isVoiceStatus(value: unknown): value is VoiceStatus {
  return value === "idle" || value === "recording" || value === "processing" || value === "playing";
}

function normalizePersistedSession(input: unknown): PersistedSession | null {
  if (!input || typeof input !== "object") {
    return null;
  }
  const candidate = input as Partial<PersistedSession>;
  if (
    candidate.version !== 1 ||
    typeof candidate.draftText !== "string" ||
    !isSystemStatus(candidate.systemStatus) ||
    typeof candidate.systemMessage !== "string" ||
    !isVoiceStatus(candidate.voiceStatus) ||
    typeof candidate.voiceProvider !== "string" ||
    typeof candidate.voiceError !== "string"
  ) {
    return null;
  }
  return {
    version: 1,
    draftText: candidate.draftText,
    systemStatus: candidate.systemStatus,
    systemMessage: candidate.systemMessage,
    voiceStatus: candidate.voiceStatus,
    voiceProvider: candidate.voiceProvider,
    voiceError: candidate.voiceError,
    updatedAt: typeof candidate.updatedAt === "number" ? candidate.updatedAt : Date.now(),
  };
}

function fileExtensionFromMime(mimeType: string): string {
  const normalized = mimeType.toLowerCase();
  if (normalized.includes("webm")) return "webm";
  if (normalized.includes("wav")) return "wav";
  if (normalized.includes("ogg")) return "ogg";
  if (normalized.includes("mp4")) return "mp4";
  if (normalized.includes("mpeg") || normalized.includes("mp3")) return "mp3";
  return "bin";
}

function extensionFromFileName(fileName: string): string {
  const index = fileName.lastIndexOf(".");
  if (index < 0) {
    return "";
  }
  return fileName.slice(index + 1).toLowerCase();
}

function isSupportedDocumentFile(file: File): boolean {
  return ALLOWED_UPLOAD_EXTENSIONS.has(extensionFromFileName(file.name));
}

function makeMessage(type: AppMessage["type"], content: string, extra?: Partial<AppMessage>): AppMessage {
  return {
    id: createId(type),
    type,
    content,
    createdAt: Date.now(),
    status: "done",
    ...extra,
  };
}

function toNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return 0;
}

function toStringSafe(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function basename(value: string): string {
  const normalized = value.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  return parts.length > 0 ? parts[parts.length - 1] : value;
}

function extractChunkCount(details: Record<string, unknown>): number {
  return Math.max(0, toNumber(details.chunk_count || details.chunks));
}

function extractSourceId(details: Record<string, unknown>, fallbackFileName: string): string {
  const sourceId = toStringSafe(details.source_id);
  if (sourceId) {
    return sourceId;
  }
  const source = toStringSafe(details.source);
  if (source) {
    return basename(source);
  }
  const file = toStringSafe(details.file);
  if (file) {
    return basename(file);
  }
  return fallbackFileName;
}

function extractDocumentId(details: Record<string, unknown>): string {
  const documentId = toStringSafe(details.document_id);
  if (documentId) {
    return documentId;
  }
  return toStringSafe(details.source_id);
}

function extractUploadedFileName(details: Record<string, unknown>, fallbackFileName: string): string {
  const fileName = toStringSafe(details.file_name);
  if (fileName) {
    return fileName;
  }
  return fallbackFileName;
}

function extractIngestStatus(resultStatus: string, details: Record<string, unknown>): string {
  const detailStatus = toStringSafe(details.status);
  if (detailStatus) {
    return detailStatus;
  }
  return resultStatus || "ok";
}

function extractBackendDetails(file: UploadFileState): Record<string, unknown> {
  if (!file.backendResponse || typeof file.backendResponse !== "object") {
    return {};
  }
  const details = file.backendResponse.details;
  if (!details || typeof details !== "object") {
    return {};
  }
  return details as Record<string, unknown>;
}

function buildUploadToastMessage(file: UploadFileState): string {
  if (file.status === "queued") {
    return `${file.fileName}: Dosya kuyruga alindi.`;
  }
  if (file.status === "uploading") {
    return `${file.fileName}: Dosya yukleniyor...`;
  }
  if (file.status === "processing") {
    return `${file.fileName}: Belge isleniyor...`;
  }
  if (file.status === "error") {
    const detail = file.errorMessage.trim();
    if (detail) {
      return `${file.fileName}: Belge yuklenemedi (${detail}).`;
    }
    return `${file.fileName}: Belge yuklenemedi.`;
  }

  const details = extractBackendDetails(file);
  const backendStatus = toStringSafe(file.backendResponse?.status);
  const fileName = extractUploadedFileName(details, file.fileName);
  const chunkCount = file.chunkCount > 0 ? file.chunkCount : extractChunkCount(details);
  const statusText = extractIngestStatus(backendStatus, details);
  if (chunkCount > 0) {
    return `${fileName}: Belge basariyla yuklendi (durum: ${statusText}, chunks: ${chunkCount}).`;
  }
  return `${fileName}: Belge basariyla yuklendi (durum: ${statusText}).`;
}

function toUploadToast(file: UploadFileState, previous?: UploadToastItem): UploadToastItem {
  const message = buildUploadToastMessage(file);
  const behavior = uploadToastBehavior(file.status);
  const now = Date.now();
  const changed = !previous || previous.status !== file.status || previous.message !== message;
  return {
    id: previous?.id || createId("toast"),
    fileId: file.id,
    fileName: file.fileName,
    status: file.status,
    message,
    updatedAt: changed ? now : previous.updatedAt,
    autoDismissMs: behavior.autoDismissMs,
    dismissible: behavior.dismissible,
  };
}

function toRecentDocuments(files: UploadFileState[], limit: number = 8): UploadedDocument[] {
  return files
    .filter((file) => file.status === "success")
    .sort((a, b) => (b.uploadedAt || b.createdAt) - (a.uploadedAt || a.createdAt))
    .slice(0, limit)
    .map((file) => ({
      fileName: file.fileName,
      sourceId: file.sourceId || file.fileName,
      documentId: file.documentId || "",
      chunkCount: file.chunkCount,
      uploadedAt: file.uploadedAt || file.createdAt,
      status: "success",
    }));
}

function buildChatContextHint(files: UploadFileState[]): ChatContextHint | undefined {
  const recentDocuments = toRecentDocuments(files, 8);
  if (recentDocuments.length === 0) {
    return undefined;
  }
  return {
    contextScope: "uploaded_documents",
    sourceIds: recentDocuments.map((doc) => doc.sourceId),
    fileNames: recentDocuments.map((doc) => doc.fileName),
    recentDocuments,
  };
}

function isDocumentIntentQuestion(text: string): boolean {
  return DOC_INTENT_PATTERN.test(text);
}

function toNumberSafe(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return undefined;
}

function normalizeCitation(input: ChatCitation): MessageSource | null {
  const fileName = typeof input.file_name === "string" ? input.file_name.trim() : "";
  if (!fileName) {
    return null;
  }
  const sourceId = typeof input.source_id === "string" ? input.source_id.trim() : "";
  const sourceType = typeof input.source_type === "string" ? input.source_type.trim() : "";
  const pageHint = typeof input.page_hint === "string" ? input.page_hint.trim() : "";
  return {
    file_name: fileName,
    source_id: sourceId || undefined,
    source_type: sourceType || undefined,
    chunk_count_used: toNumberSafe(input.chunk_count_used),
    page_hint: pageHint || undefined,
  };
}

function buildAssistantSources(response: ChatResponse): MessageSource[] {
  const normalizedFromApi = Array.isArray(response.citations)
    ? response.citations
        .map(normalizeCitation)
        .filter((item): item is MessageSource => item !== null)
    : [];

  const fallbackFileNames = Array.from(
    new Set(
      [...(response.doc_sources || []), ...(response.matched_file_names || [])]
        .map((value) => String(value || "").trim())
        .filter(Boolean),
    ),
  );
  const fallbackSources: MessageSource[] =
    normalizedFromApi.length > 0
      ? []
      : fallbackFileNames.map((fileName, index) => ({
          file_name: fileName,
          source_id: response.matched_source_ids?.[index] || undefined,
        }));

  const merged = normalizedFromApi.length > 0 ? normalizedFromApi : fallbackSources;
  const dedup = new Map<string, MessageSource>();
  for (const source of merged) {
    const key = `${source.source_id || ""}::${source.file_name}`;
    if (!dedup.has(key)) {
      dedup.set(key, source);
      continue;
    }
    const current = dedup.get(key) as MessageSource;
    const totalChunks = (current.chunk_count_used || 0) + (source.chunk_count_used || 0);
    dedup.set(key, {
      ...current,
      chunk_count_used: totalChunks > 0 ? totalChunks : undefined,
    });
  }
  return Array.from(dedup.values());
}

export default function MainAppPage() {
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const currentUserExternalId = user?.external_id || null;

  const messages = useMessageStore((state) => state.messages);
  const messageActiveUserId = useMessageStore((state) => state.activeUserId);
  const addMessage = useMessageStore((state) => state.addMessage);
  const setActiveMessageUser = useMessageStore((state) => state.setActiveUser);
  const clearActiveUserMessageCache = useMessageStore((state) => state.clearActiveUserCache);

  const voiceStatus = useVoiceStore((state) => state.status);
  const voiceProvider = useVoiceStore((state) => state.provider);
  const voiceError = useVoiceStore((state) => state.error);
  const setVoiceStatus = useVoiceStore((state) => state.setStatus);
  const setVoiceProvider = useVoiceStore((state) => state.setProvider);
  const setVoiceError = useVoiceStore((state) => state.setError);

  const setActiveUploadUser = useUploadStore((state) => state.setActiveUser);
  const clearActiveUserUploadCache = useUploadStore((state) => state.clearActiveUserCache);

  const upload = useUploadStore((state) => ({
    inProgress: state.inProgress,
    files: state.files,
    enqueueFiles: state.enqueueFiles,
    addRejectedFile: state.addRejectedFile,
    markUploading: state.markUploading,
    markProcessing: state.markProcessing,
    setProgress: state.setProgress,
    markSuccess: state.markSuccess,
    markError: state.markError,
  }));

  const systemStatus = useAppStore((state) => state.systemStatus);
  const systemMessage = useAppStore((state) => state.systemMessage);
  const setSystemState = useAppStore((state) => state.setSystemState);

  const [text, setText] = useState("");
  const [uploadToasts, setUploadToasts] = useState<UploadToastItem[]>([]);
  const dismissedUploadToastsRef = useRef<Set<string>>(new Set());
  const voiceActionInFlightRef = useRef(false);
  const audioUrlsRef = useRef<string[]>([]);
  const recorder = useRecorder();
  const busy = useMemo(() => voiceStatus === "processing", [voiceStatus]);

  const dismissUploadToast = useCallback((fileId: string, status: UploadFileState["status"]) => {
    dismissedUploadToastsRef.current.add(uploadToastSignature(fileId, status));
    setUploadToasts((previous) => previous.filter((toast) => !(toast.fileId === fileId && toast.status === status)));
  }, []);

  useEffect(() => {
    setActiveMessageUser(currentUserExternalId);
    setActiveUploadUser(currentUserExternalId);
  }, [currentUserExternalId, setActiveMessageUser, setActiveUploadUser]);

  useEffect(() => {
    dismissedUploadToastsRef.current.clear();
    setUploadToasts([]);
  }, [currentUserExternalId]);

  useEffect(() => {
    setUploadToasts((previous) => {
      const previousByFileId = new Map(previous.map((toast) => [toast.fileId, toast]));
      const next: UploadToastItem[] = [];

      for (const file of upload.files) {
        const signature = uploadToastSignature(file.id, file.status);
        if (dismissedUploadToastsRef.current.has(signature)) {
          continue;
        }
        const previousToast = previousByFileId.get(file.id);
        next.push(toUploadToast(file, previousToast));
      }

      next.sort((left, right) => right.updatedAt - left.updatedAt);
      return next;
    });
  }, [upload.files]);

  useEffect(() => {
    if (!currentUserExternalId) {
      setText("");
      return;
    }
    const cached = normalizePersistedSession(readJsonFromStorage(sessionStorageKey(currentUserExternalId)));
    if (!cached) {
      return;
    }
    setText(cached.draftText);
    setSystemState(cached.systemStatus, cached.systemMessage);
    setVoiceStatus(cached.voiceStatus);
    setVoiceProvider(cached.voiceProvider);
    setVoiceError(cached.voiceError);
  }, [currentUserExternalId, setSystemState, setVoiceError, setVoiceProvider, setVoiceStatus]);

  useEffect(() => {
    if (messageActiveUserId !== currentUserExternalId) {
      return;
    }
    if (messages.length > 0) {
      return;
    }
    addMessage(makeMessage("system", SystemMessages.ready));
  }, [addMessage, currentUserExternalId, messageActiveUserId, messages.length]);

  useEffect(() => {
    if (!currentUserExternalId) {
      return;
    }
    scheduleSessionCacheForUser(currentUserExternalId, {
      version: 1,
      draftText: text,
      systemStatus,
      systemMessage,
      voiceStatus,
      voiceProvider,
      voiceError,
      updatedAt: Date.now(),
    } satisfies PersistedSession);
  }, [currentUserExternalId, systemMessage, systemStatus, text, voiceError, voiceProvider, voiceStatus]);

  useEffect(() => {
    if (!recorder.error) {
      return;
    }
    setVoiceStatus("idle");
    setVoiceError(recorder.error);
    setSystemState("error", recorder.error);
    addMessage(makeMessage("error", `Microphone error: ${recorder.error}`));
  }, [addMessage, recorder.error, setSystemState, setVoiceError, setVoiceStatus]);

  useEffect(() => {
    return () => {
      for (const url of audioUrlsRef.current) {
        URL.revokeObjectURL(url);
      }
      audioUrlsRef.current = [];
    };
  }, []);

  const onSendText = useCallback(async () => {
    const message = text.trim();
    if (!token || !message || busy || recorder.isRecording) {
      return;
    }

    const latestFiles = useUploadStore.getState().files;
    const contextHint = buildChatContextHint(latestFiles);

    addMessage(makeMessage("user_text", message));
    setText("");
    setSystemState("loading", SystemMessages.aiReplyPreparing);

    try {
      const response = await sendChatMessage({
        token,
        userId: currentUserExternalId || undefined,
        message,
        includeReflectionContext: true,
        saveToLongTerm: true,
        contextHint,
      });

      const assistantSources = buildAssistantSources(response);
      const assistantMeta: AppMessage["meta"] = {
        context_hits: response.context_hits ?? 0,
        memory_size: response.memory_size ?? 0,
        doc_context_hits: response.doc_context_hits ?? 0,
      };
      if (assistantSources.length > 0) {
        assistantMeta.sources = assistantSources;
      }

      addMessage(
        makeMessage("assistant_text", response.reply, {
          meta: assistantMeta,
        }),
      );
      setSystemState("success", SystemMessages.replyReady);

      if ((response.doc_context_hits || 0) === 0 && contextHint && isDocumentIntentQuestion(message)) {
        addMessage(makeMessage("system", retrievalNoHit()));
      }
    } catch (err) {
      const detail = err instanceof Error ? err.message : SystemMessages.messageSendFailed;
      addMessage(makeMessage("error", `Chat error: ${detail}`));
      setSystemState("error", detail);
    }
  }, [addMessage, busy, currentUserExternalId, recorder.isRecording, setSystemState, text, token]);

  const onRequestMicPermission = useCallback(async () => {
    const granted = await recorder.requestPermission();
    if (granted) {
      setSystemState("success", SystemMessages.microphonePermissionGranted);
      addMessage(makeMessage("system", SystemMessages.microphoneReady));
    } else {
      const detail = recorder.error || recorder.supportMessage || SystemMessages.microphonePermissionDenied;
      setSystemState("error", detail);
      addMessage(makeMessage("error", detail));
    }
  }, [addMessage, recorder, setSystemState]);

  const onVoiceToggle = useCallback(async () => {
    if (!token || busy || voiceActionInFlightRef.current) {
      return;
    }
    voiceActionInFlightRef.current = true;

    try {
      if (!recorder.isRecording) {
        if (!recorder.isSupported) {
          const detail = recorder.supportMessage;
          setSystemState("error", detail);
          addMessage(makeMessage("error", detail));
          return;
        }

        const started = await recorder.startRecording();
        if (started) {
          setVoiceStatus("recording");
          setSystemState("loading", SystemMessages.recordingStarted);
        }
        return;
      }

      setVoiceStatus("processing");
      setSystemState("loading", SystemMessages.voicePreparing);
      const blob = await recorder.stopRecording();
      if (!blob) {
        throw new Error(SystemMessages.voiceRecordFailed);
      }

      const mimeType = blob.type || recorder.mimeType || "audio/webm";
      const extension = fileExtensionFromMime(mimeType);
      const file = new File([blob], `voice-${Date.now()}.${extension}`, { type: mimeType });

      const response = await chatWithVoice({
        token,
        file,
        language: "tr",
        includeReflectionContext: true,
        audioFormat: "mp3",
      });

      if (response.transcript) {
        addMessage(
          makeMessage("user_voice", response.transcript, {
            transcript: response.transcript,
            meta: {
              stt_provider: response.stt_provider,
            },
          }),
        );
      }

      let audioUrl: string | undefined;
      if (response.audio_url) {
        audioUrl = await getAudioObjectUrl({ token, audioPath: response.audio_url });
        audioUrlsRef.current.push(audioUrl);
      }

      addMessage(
        makeMessage(audioUrl ? "assistant_voice" : "assistant_text", response.reply, {
          audioUrl,
          transcript: response.transcript,
          fileName: response.audio_file,
          meta: {
            tts_provider: response.tts_provider,
            stt_provider: response.stt_provider,
            tts_voice: response.tts_voice || "",
          },
        }),
      );

      setVoiceProvider(response.tts_provider);
      setVoiceStatus("idle");
      setSystemState("success", `Voice reply ready (TTS: ${response.tts_provider}).`);
    } catch (err) {
      const detail = err instanceof Error ? err.message : SystemMessages.voiceFailed;
      setVoiceError(detail);
      setVoiceStatus("idle");
      setSystemState("error", detail);
      addMessage(makeMessage("error", `Voice error: ${detail}`));
    } finally {
      voiceActionInFlightRef.current = false;
    }
  }, [
    addMessage,
    busy,
    recorder,
    setSystemState,
    setVoiceError,
    setVoiceProvider,
    setVoiceStatus,
    token,
    voiceActionInFlightRef,
  ]);

  const onUploadFiles = useCallback(
    async (selectedFiles: File[]) => {
      if (!token || selectedFiles.length === 0) {
        return;
      }

      const validFiles: File[] = [];

      for (const file of selectedFiles) {
        if (!isSupportedDocumentFile(file)) {
          const detail = SystemMessages.unsupportedFileType;
          upload.addRejectedFile(file, detail);
          continue;
        }

        if (file.size > MAX_UPLOAD_FILE_SIZE_BYTES) {
          const detail = oversizedFile(MAX_UPLOAD_SIZE_MB);
          upload.addRejectedFile(file, detail);
          continue;
        }

        validFiles.push(file);
      }

      if (validFiles.length === 0) {
        setSystemState("error", SystemMessages.noEligibleFiles);
        return;
      }

      const queuedStates = upload.enqueueFiles(validFiles);
      const tasks: UploadTask[] = queuedStates.map((state, index) => ({ state, file: validFiles[index] }));

      setSystemState("loading", queueSummary(tasks.length));

      let cursor = 0;
      let successCount = 0;
      let errorCount = 0;

      const worker = async () => {
        while (cursor < tasks.length) {
          const index = cursor;
          cursor += 1;

          const task = tasks[index];
          const { state, file } = task;

          upload.markUploading(state.id);
          setSystemState("loading", "Belge isleniyor...");

          try {
            let movedToProcessing = false;
            const result = await uploadDocument({
              token,
              file,
              category: "general",
              onProgress: (progress) => {
                upload.setProgress(state.id, progress);
                if (!movedToProcessing && progress >= 100) {
                  movedToProcessing = true;
                  upload.markProcessing(state.id);
                }
              },
            });

            const chunkCount = extractChunkCount(result.details);
            const sourceId = extractSourceId(result.details, file.name);
            const documentId = extractDocumentId(result.details);

            upload.markProcessing(state.id);
            upload.markSuccess(state.id, {
              backendResponse: {
                status: result.status,
                details: result.details,
              },
              sourceId,
              documentId,
              chunkCount,
              uploadedAt: Date.now(),
            });

            successCount += 1;
          } catch (err) {
            const detail = err instanceof Error ? err.message : SystemMessages.documentUploadFailed;
            upload.markError(state.id, detail);
            errorCount += 1;
          }
        }
      };

      const workers = Array.from({ length: Math.min(UPLOAD_CONCURRENCY_LIMIT, tasks.length) }, () => worker());
      await Promise.all(workers);

      const summary = uploadSummary(successCount, errorCount);
      if (errorCount > 0 && successCount === 0) {
        setSystemState("error", summary);
      } else {
        setSystemState("success", summary);
      }

    },
    [setSystemState, token, upload],
  );

  const onLogout = useCallback(() => {
    clearSessionCacheForUser(currentUserExternalId);
    clearActiveUserUploadCache();
    clearActiveUserMessageCache({
      clearPersisted: CLEAR_PERSISTED_MESSAGES_ON_LOGOUT_DEFAULT,
    });
    clearAuth();
  }, [clearActiveUserMessageCache, clearActiveUserUploadCache, clearAuth, currentUserExternalId]);

  if (!token) {
    return null;
  }

  return (
    <div className="relative flex h-[100dvh] min-h-[100svh] flex-col overflow-hidden bg-slate-950 text-slate-100">
      <TopBar user={user} onLogout={onLogout} showAdminSwitch={Boolean(user?.is_admin)} />
      <UploadToastStack toasts={uploadToasts} onDismiss={dismissUploadToast} />
      <StatusIndicator voiceStatus={voiceStatus} systemStatus={systemStatus} message={systemMessage} />

      <MessageList
        messages={messages}
        onAudioPlay={() => {
          setVoiceStatus("playing");
          setSystemState("loading", SystemMessages.voicePlaying);
        }}
        onAudioEnded={() => {
          setVoiceStatus("idle");
          setSystemState("idle", SystemMessages.idle);
        }}
      />

      <Composer
        text={text}
        busy={busy}
        isRecording={recorder.isRecording}
        voiceStatus={voiceStatus}
        uploadInProgress={upload.inProgress}
        onTextChange={setText}
        onSend={onSendText}
        onVoiceToggle={onVoiceToggle}
        onUploadFiles={onUploadFiles}
        onRequestMicPermission={onRequestMicPermission}
        maxUploadSizeMb={MAX_UPLOAD_SIZE_MB}
      />
    </div>
  );
}
