import { create } from "zustand";

import type { UploadFileState } from "../types/upload";
import { createId } from "../utils/id";
import {
  createThrottledStorageWriter,
  readJsonFromStorage,
  recentDocsStorageKey,
  removeStorageKey,
} from "./persistence";

const recentDocsWriter = createThrottledStorageWriter();

function hasActiveUploads(files: UploadFileState[]): boolean {
  return files.some((file) => file.status === "queued" || file.status === "uploading" || file.status === "processing");
}

function isValidStatus(value: unknown): value is UploadFileState["status"] {
  return value === "queued" || value === "uploading" || value === "processing" || value === "success" || value === "error";
}

function normalizeStoredFile(input: unknown): UploadFileState | null {
  if (!input || typeof input !== "object") {
    return null;
  }
  const candidate = input as Partial<UploadFileState>;
  if (
    typeof candidate.id !== "string" ||
    typeof candidate.fileName !== "string" ||
    !isValidStatus(candidate.status) ||
    typeof candidate.progress !== "number" ||
    typeof candidate.sizeBytes !== "number" ||
    typeof candidate.mimeType !== "string" ||
    typeof candidate.createdAt !== "number" ||
    typeof candidate.errorMessage !== "string"
  ) {
    return null;
  }

  const status =
    candidate.status === "queued" || candidate.status === "uploading" || candidate.status === "processing"
      ? "error"
      : candidate.status;

  return {
    id: candidate.id,
    fileName: candidate.fileName,
    status,
    progress: Math.max(0, Math.min(100, candidate.progress)),
    sizeBytes: Math.max(0, candidate.sizeBytes),
    mimeType: candidate.mimeType,
    createdAt: candidate.createdAt,
    errorMessage:
      status === "error" && !candidate.errorMessage
        ? "Yukleme kesintiye ugradi. Gerekirse dosyayi yeniden yukleyin."
        : candidate.errorMessage,
    sourceId: typeof candidate.sourceId === "string" ? candidate.sourceId : candidate.fileName,
    documentId: typeof candidate.documentId === "string" ? candidate.documentId : "",
    chunkCount: typeof candidate.chunkCount === "number" ? Math.max(0, candidate.chunkCount) : 0,
    uploadedAt: typeof candidate.uploadedAt === "number" ? candidate.uploadedAt : null,
    backendResponse:
      candidate.backendResponse && typeof candidate.backendResponse === "object"
        ? (candidate.backendResponse as Record<string, unknown>)
        : null,
  };
}

function loadFiles(userId: string): UploadFileState[] {
  const parsed = readJsonFromStorage(recentDocsStorageKey(userId));
  if (!Array.isArray(parsed)) {
    return [];
  }
  return parsed.map(normalizeStoredFile).filter((item): item is UploadFileState => item !== null);
}

function schedulePersistFiles(userId: string, files: UploadFileState[]): void {
  recentDocsWriter.schedule(recentDocsStorageKey(userId), files);
}

function clearPersistedFiles(userId: string): void {
  const key = recentDocsStorageKey(userId);
  recentDocsWriter.cancel(key);
  removeStorageKey(key);
}

function patchFileState(
  files: UploadFileState[],
  id: string,
  updater: (file: UploadFileState) => UploadFileState,
): UploadFileState[] {
  return files.map((file) => (file.id === id ? updater(file) : file));
}

type UploadState = {
  activeUserId: string | null;
  files: UploadFileState[];
  inProgress: boolean;
  setActiveUser: (userId: string | null) => void;
  enqueueFiles: (files: File[]) => UploadFileState[];
  addRejectedFile: (file: File, errorMessage: string) => UploadFileState;
  markUploading: (id: string) => void;
  markProcessing: (id: string) => void;
  setProgress: (id: string, progress: number) => void;
  markSuccess: (
    id: string,
    payload: {
      backendResponse: Record<string, unknown>;
      sourceId?: string;
      documentId?: string;
      chunkCount?: number;
      uploadedAt?: number;
    },
  ) => void;
  markError: (id: string, errorMessage: string) => void;
  clearQueue: () => void;
  clearActiveUserCache: () => void;
};

export const useUploadStore = create<UploadState>((set, get) => ({
  activeUserId: null,
  files: [],
  inProgress: false,
  setActiveUser: (userId) => {
    const nextUserId = (userId || "").trim() || null;
    const previousUserId = get().activeUserId;
    if (previousUserId) {
      recentDocsWriter.flush(recentDocsStorageKey(previousUserId));
    }
    if (!nextUserId) {
      set({ activeUserId: null, files: [], inProgress: false });
      return;
    }
    const files = loadFiles(nextUserId);
    set({
      activeUserId: nextUserId,
      files,
      inProgress: hasActiveUploads(files),
    });
  },
  enqueueFiles: (incomingFiles) => {
    const createdAt = Date.now();
    const queued = incomingFiles.map<UploadFileState>((file, index) => ({
      id: createId("upload"),
      fileName: file.name,
      status: "queued",
      progress: 0,
      sizeBytes: file.size,
      mimeType: file.type || "application/octet-stream",
      createdAt: createdAt + index,
      errorMessage: "",
      sourceId: file.name,
      documentId: "",
      chunkCount: 0,
      uploadedAt: null,
      backendResponse: null,
    }));

    set((state) => {
      const files = [...state.files, ...queued];
      if (state.activeUserId) {
        schedulePersistFiles(state.activeUserId, files);
      }
      return {
        files,
        inProgress: hasActiveUploads(files),
      };
    });

    return queued;
  },
  addRejectedFile: (file, errorMessage) => {
    const item: UploadFileState = {
      id: createId("upload"),
      fileName: file.name,
      status: "error",
      progress: 0,
      sizeBytes: file.size,
      mimeType: file.type || "application/octet-stream",
      createdAt: Date.now(),
      errorMessage,
      sourceId: file.name,
      documentId: "",
      chunkCount: 0,
      uploadedAt: null,
      backendResponse: null,
    };

    set((state) => {
      const files = [...state.files, item];
      if (state.activeUserId) {
        schedulePersistFiles(state.activeUserId, files);
      }
      return {
        files,
        inProgress: hasActiveUploads(files),
      };
    });

    return item;
  },
  markUploading: (id) =>
    set((state) => {
      const files = patchFileState(state.files, id, (file) => ({
        ...file,
        status: "uploading",
        errorMessage: "",
      }));
      if (state.activeUserId) {
        schedulePersistFiles(state.activeUserId, files);
      }
      return { files, inProgress: hasActiveUploads(files) };
    }),
  markProcessing: (id) =>
    set((state) => {
      const files = patchFileState(state.files, id, (file) => ({
        ...file,
        status: file.status === "success" ? file.status : "processing",
        progress: 100,
      }));
      if (state.activeUserId) {
        schedulePersistFiles(state.activeUserId, files);
      }
      return { files, inProgress: hasActiveUploads(files) };
    }),
  setProgress: (id, progress) =>
    set((state) => {
      const safeProgress = Math.max(0, Math.min(100, progress));
      const files = patchFileState(state.files, id, (file) => ({
        ...file,
        progress: safeProgress,
        status:
          safeProgress >= 100 && (file.status === "uploading" || file.status === "queued") ? "processing" : file.status,
      }));
      if (state.activeUserId) {
        schedulePersistFiles(state.activeUserId, files);
      }
      return { files, inProgress: hasActiveUploads(files) };
    }),
  markSuccess: (id, payload) =>
    set((state) => {
      const files = patchFileState(state.files, id, (file) => ({
        ...file,
        status: "success",
        progress: 100,
        errorMessage: "",
        sourceId: payload.sourceId || file.sourceId,
        documentId: payload.documentId || file.documentId,
        chunkCount: payload.chunkCount ?? file.chunkCount,
        uploadedAt: payload.uploadedAt ?? Date.now(),
        backendResponse: payload.backendResponse,
      }));
      if (state.activeUserId) {
        schedulePersistFiles(state.activeUserId, files);
      }
      return { files, inProgress: hasActiveUploads(files) };
    }),
  markError: (id, errorMessage) =>
    set((state) => {
      const files = patchFileState(state.files, id, (file) => ({
        ...file,
        status: "error",
        errorMessage,
      }));
      if (state.activeUserId) {
        schedulePersistFiles(state.activeUserId, files);
      }
      return { files, inProgress: hasActiveUploads(files) };
    }),
  clearQueue: () =>
    set((state) => {
      if (state.activeUserId) {
        schedulePersistFiles(state.activeUserId, []);
      }
      return { files: [], inProgress: false };
    }),
  clearActiveUserCache: () => {
    const activeUserId = get().activeUserId;
    if (activeUserId) {
      clearPersistedFiles(activeUserId);
    }
    set({ files: [], inProgress: false });
  },
}));
