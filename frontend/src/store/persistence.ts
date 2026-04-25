export const STORAGE_WRITE_THROTTLE_MS = 400;
export const CLEAR_PERSISTED_MESSAGES_ON_LOGOUT_DEFAULT = false;

const STORAGE_PREFIX = "boranizm";
const sessionCacheWriter = createThrottledStorageWriter();

export function messagesStorageKey(userId: string): string {
  return `${STORAGE_PREFIX}:messages:${userId}`;
}

export function recentDocsStorageKey(userId: string): string {
  return `${STORAGE_PREFIX}:recent_docs:${userId}`;
}

export function sessionStorageKey(userId: string): string {
  return `${STORAGE_PREFIX}:session:${userId}`;
}

function storageAvailable(): boolean {
  return typeof localStorage !== "undefined";
}

function safeRemove(key: string): void {
  if (!storageAvailable()) {
    return;
  }
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore storage errors
  }
}

export function readJsonFromStorage(key: string): unknown {
  if (!storageAvailable()) {
    return null;
  }
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as unknown;
  } catch {
    safeRemove(key);
    return null;
  }
}

export function writeJsonToStorage(key: string, value: unknown): void {
  if (!storageAvailable()) {
    return;
  }
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore storage errors
  }
}

export function removeStorageKey(key: string): void {
  safeRemove(key);
}

export function clearSessionCacheForUser(userId: string | null | undefined): void {
  const scopedUserId = (userId || "").trim();
  if (!scopedUserId) {
    return;
  }
  const key = sessionStorageKey(scopedUserId);
  sessionCacheWriter.cancel(key);
  safeRemove(key);
}

export function scheduleSessionCacheForUser(userId: string | null | undefined, payload: unknown): void {
  const scopedUserId = (userId || "").trim();
  if (!scopedUserId) {
    return;
  }
  sessionCacheWriter.schedule(sessionStorageKey(scopedUserId), payload);
}

type TimeoutHandle = ReturnType<typeof setTimeout>;

export function createThrottledStorageWriter(delayMs: number = STORAGE_WRITE_THROTTLE_MS): {
  schedule: (key: string, value: unknown) => void;
  flush: (key?: string) => void;
  cancel: (key?: string) => void;
} {
  const timers = new Map<string, TimeoutHandle>();
  const payloads = new Map<string, unknown>();

  const runWrite = (key: string): void => {
    const payload = payloads.get(key);
    payloads.delete(key);
    timers.delete(key);
    if (payload === undefined) {
      return;
    }
    writeJsonToStorage(key, payload);
  };

  return {
    schedule: (key, value) => {
      payloads.set(key, value);
      if (timers.has(key)) {
        return;
      }
      const timer = setTimeout(() => runWrite(key), Math.max(0, delayMs));
      timers.set(key, timer);
    },
    flush: (key) => {
      if (key) {
        const timer = timers.get(key);
        if (timer) {
          clearTimeout(timer);
          timers.delete(key);
        }
        runWrite(key);
        return;
      }
      for (const timer of timers.values()) {
        clearTimeout(timer);
      }
      const keys = Array.from(payloads.keys());
      timers.clear();
      for (const targetKey of keys) {
        runWrite(targetKey);
      }
    },
    cancel: (key) => {
      if (key) {
        const timer = timers.get(key);
        if (timer) {
          clearTimeout(timer);
          timers.delete(key);
        }
        payloads.delete(key);
        return;
      }
      for (const timer of timers.values()) {
        clearTimeout(timer);
      }
      timers.clear();
      payloads.clear();
    },
  };
}
