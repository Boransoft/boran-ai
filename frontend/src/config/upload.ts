const DEFAULT_MAX_UPLOAD_SIZE_MB = 100;
const MIN_UPLOAD_SIZE_MB = 1;
const MAX_UPLOAD_SIZE_MB_HARD_LIMIT = 500;

function parseUploadSizeMb(value: unknown): number {
  if (typeof value !== "string" || !value.trim()) {
    return DEFAULT_MAX_UPLOAD_SIZE_MB;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_MAX_UPLOAD_SIZE_MB;
  }
  const rounded = Math.floor(parsed);
  if (rounded < MIN_UPLOAD_SIZE_MB) {
    return DEFAULT_MAX_UPLOAD_SIZE_MB;
  }
  if (rounded > MAX_UPLOAD_SIZE_MB_HARD_LIMIT) {
    return MAX_UPLOAD_SIZE_MB_HARD_LIMIT;
  }
  return rounded;
}

export const MAX_UPLOAD_SIZE_MB = parseUploadSizeMb(import.meta.env.VITE_MAX_UPLOAD_SIZE_MB);
export const MAX_UPLOAD_FILE_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;
