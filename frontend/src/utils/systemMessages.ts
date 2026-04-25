import type { UploadedDocument } from "../types/context";

export const SystemMessages = {
  ready: "Haz\u0131r\u0131m. Metin yazabilir, ses kayd\u0131 g\u00f6nderebilir veya belge y\u00fckleyebilirsin.",
  aiReplyPreparing: "AI yan\u0131t\u0131 haz\u0131rlan\u0131yor...",
  replyReady: "Yan\u0131t haz\u0131r.",
  messageSendFailed: "Mesaj g\u00f6nderilemedi.",
  microphonePermissionGranted: "Mikrofon izni verildi.",
  microphoneReady: "Mikrofon izni haz\u0131r.",
  microphonePermissionDenied: "Mikrofon izni reddedildi.",
  recordingStarted: "Kay\u0131t ba\u015flad\u0131. Tekrar bas\u0131nca g\u00f6nderilir.",
  voicePreparing: "Ses \u00e7\u00f6z\u00fcmleme ve yan\u0131t haz\u0131rlan\u0131yor...",
  voiceRecordFailed: "Ses kayd\u0131 al\u0131namad\u0131.",
  voiceFailed: "Voice chat ba\u015far\u0131s\u0131z.",
  voicePlaying: "Sesli yan\u0131t oynat\u0131l\u0131yor...",
  idle: "Haz\u0131r",
  connectionError: "Ba\u011flant\u0131 hatas\u0131 olu\u015ftu.",
  documentUploadFailed: "Belge y\u00fcklenemedi.",
  unsupportedFileType: "Desteklenmeyen dosya tipi.",
  noEligibleFiles: "Y\u00fcklemeye uygun dosya bulunamad\u0131.",
} as const;

export function oversizedFile(maxUploadSizeMb: number): string {
  return `Dosya boyutu ${maxUploadSizeMb} MB s\u0131n\u0131r\u0131n\u0131 a\u015f\u0131yor.`;
}

export function uploadQueued(fileName: string): string {
  return `${fileName} kuyru\u011fa al\u0131nd\u0131.`;
}

export function uploadStarted(fileName: string): string {
  return `${fileName} y\u00fckleniyor...`;
}

export function uploadProcessing(fileName: string): string {
  return `${fileName}: Belge i\u015fleniyor...`;
}

export function uploadProcessed(fileName: string, chunkCount: number, statusText: string): string {
  const normalizedStatus = statusText.trim() || "ok";
  if (chunkCount > 0) {
    return `${fileName}: Belge i\u015flendi. Art\u0131k bu belge hakk\u0131nda soru sorabilirsin. (durum: ${normalizedStatus}, chunks: ${chunkCount})`;
  }
  return `${fileName}: Belge i\u015flendi. Art\u0131k bu belge hakk\u0131nda soru sorabilirsin. (durum: ${normalizedStatus})`;
}

export function uploadSuccess(fileName: string, chunkCount: number): string {
  return uploadProcessed(fileName, chunkCount, "ok");
}

export function uploadFailed(fileName: string, detail: string): string {
  return `${fileName} y\u00fcklenemedi: ${detail}`;
}

export function queueSummary(total: number): string {
  return `${total} belge y\u00fckleme kuyru\u011funa al\u0131nd\u0131.`;
}

export function uploadSummary(successCount: number, errorCount: number): string {
  if (errorCount > 0 && successCount > 0) {
    return `${successCount} dosya y\u00fcklendi, ${errorCount} dosya hata verdi.`;
  }
  if (errorCount > 0) {
    return `${errorCount} dosya y\u00fcklenemedi.`;
  }
  return `${successCount} dosya ba\u015far\u0131yla y\u00fcklendi.`;
}

export function retrievalGuidance(recentDocuments: UploadedDocument[]): string {
  if (recentDocuments.length === 0) {
    return "Daha iyi sonu\u00e7 i\u00e7in daha spesifik soru sorabilirsin.";
  }
  const top = recentDocuments
    .slice(0, 3)
    .map((doc) => `\"${doc.fileName}\"`)
    .join(", ");
  return `Belgeler \u00f6\u011frenme pipeline'\u0131na g\u00f6nderildi. \u00d6rne\u011fin ${top} hakk\u0131nda daha spesifik soru sorabilirsin.`;
}

export function retrievalNoHit(): string {
  return "Y\u00fcklenen belgelerde bu soruya dair net bir i\u00e7erik bulamad\u0131m. \u0130stersen belge ad\u0131 vererek daha spesifik sor.";
}
