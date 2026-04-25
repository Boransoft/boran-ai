export const ADMIN_TAB_LABELS = {
  dashboard: "Gösterge Paneli",
  documents: "Belgeler",
  jobs: "İşleme İşleri",
  conversations: "Konuşmalar",
  logs: "Kayıtlar",
  chunks: "Parça İnceleme",
} as const;

export const ADMIN_STATUS_LABELS: Record<string, string> = {
  ready: "Hazır",
  completed: "Tamamlandı",
  success: "Başarılı",
  ok: "Tamam",
  queued: "Kuyrukta",
  pending: "Beklemede",
  waiting: "Bekliyor",
  running: "Çalışıyor",
  active: "Aktif",
  processing: "İşleniyor",
  failed: "Hatalı",
  error: "Hata",
  critical: "Kritik",
  retried: "Yeniden Denendi",
  uploaded: "Yüklendi",
  unknown: "Bilinmiyor",
} as const;

export const ADMIN_LOG_LEVEL_LABELS: Record<string, string> = {
  ERROR: "HATA",
  CRITICAL: "KRİTİK",
  WARNING: "UYARI",
  INFO: "BİLGİ",
  DEBUG: "AYRINTI",
} as const;

export const ADMIN_STAGE_LABELS: Record<string, string> = {
  ingest: "İşleme",
  running: "Çalışıyor",
  completed: "Tamamlandı",
  failed: "Hatalı",
} as const;

export const ADMIN_SOURCE_TYPE_LABELS: Record<string, string> = {
  pdf: "PDF",
  image: "Görsel",
  document: "Doküman",
  text: "Metin",
} as const;

export const ADMIN_COMPONENT_LABELS: Record<string, string> = {
  backend: "Arka Uç",
  system: "Sistem",
} as const;

export const ADMIN_ROLE_LABELS: Record<string, string> = {
  user: "Kullanıcı",
  assistant: "Asistan",
  system: "Sistem",
  message: "Mesaj",
} as const;

export function toAdminStatusLabel(status: string): string {
  const key = status.trim().toLowerCase();
  if (!key) return "-";
  return ADMIN_STATUS_LABELS[key] || status;
}

export function toAdminLogLevelLabel(level: string): string {
  const key = level.trim().toUpperCase();
  if (!key) return "-";
  return ADMIN_LOG_LEVEL_LABELS[key] || key;
}

export function toAdminStageLabel(stage: string): string {
  const key = stage.trim().toLowerCase();
  if (!key) return "-";
  return ADMIN_STAGE_LABELS[key] || stage;
}

export function toAdminSourceTypeLabel(sourceType: string): string {
  const key = sourceType.trim().toLowerCase();
  if (!key) return "-";
  return ADMIN_SOURCE_TYPE_LABELS[key] || sourceType;
}

export function toAdminComponentLabel(component: string): string {
  const key = component.trim().toLowerCase();
  if (!key) return "-";
  return ADMIN_COMPONENT_LABELS[key] || component;
}

export function toAdminRoleLabel(role: string): string {
  const key = role.trim().toLowerCase();
  if (!key) return "-";
  return ADMIN_ROLE_LABELS[key] || role;
}

export const ADMIN_TEXTS = {
  pageTitle: "İç Yönetim Paneli",
  pageSubtitle: "Operasyonel görünürlük",
  refresh: "Yenile",
  loading: "Yükleniyor...",
  loadError: "Admin verisi yüklenemedi.",
  noData: "Veri yok.",
  missingTablesPrefix: "Eksik faz-1 tabloları:",
  selectedCount: (count: number) => `${count} belge seçildi`,
  filters: {
    allStatuses: "Tüm durumlar",
    allLevels: "Tüm seviyeler",
    fileSearch: "Dosya adı, belge ID veya kullanıcı ara...",
    componentSearch: "Bileşen ara...",
  },
  metrics: {
    totalDocuments: "Toplam Belgeler",
    totalUsers: "Toplam Kullanıcı",
    totalChunks: "Toplam Parça",
    activeJobs: "Aktif İşler",
    queuedJobs: "Kuyruktaki İşler",
    failedJobs: "Hatalı İşler",
    recentErrors: "Son Hatalar",
    recentConversations: "Son Konuşmalar",
    recentDocuments: "Son Yüklenen Belgeler",
    totalChunksLabel: "Toplam parça",
  },
  panels: {
    documentDetail: "Belge Detayı",
    conversationDetail: "Konuşma Detayı",
    jobDetail: "İş Detayı",
    logDetail: "Kayıt Detayı",
    chunkSamples: "Örnek Parçalar",
    relatedRecords: "İlişkili kayıtlar",
    rawLogRecord: "Ham Kayıt",
  },
  fields: {
    document: "Belge",
    documentId: "Belge ID",
    userId: "Kullanıcı ID",
    status: "Durum",
    category: "Kategori",
    tags: "Etiketler",
    source: "Kaynak",
    filePath: "Dosya yolu",
    conversationId: "Konuşma ID",
    level: "Seviye",
    component: "Bileşen",
    time: "Zaman",
    jobId: "İş ID",
    retryCount: "Tekrar sayısı",
    errorMessage: "Hata mesajı",
    chunk: "Parça",
  },
  labels: {
    relatedDocument: "Belge",
    relatedConversation: "Konuşma",
    relatedJob: "İş",
  },
  actions: {
    applyFilter: "Filtrele",
    clearFilter: "Filtreyi Temizle",
    openDetail: "Detay",
    open: "Aç",
    showRecentMessages: "Son Mesajlar",
    goToDocument: "Belgeye Git",
    goToDocuments: "Belgelere Git",
    goToConversations: "Konuşmalara Git",
    goToLogs: "Kayıtlara Git",
    goToJobs: "İşlere Git",
    goToRelatedRecord: "İlişkili Kayda Git",
    userDocuments: "Kullanıcı Belgeleri",
    retry: "Tekrar Dene",
    retryFailed: "Hatalıları Yeniden Başlat",
    reprocess: "Yeniden İşle",
    relearn: "Yeniden Öğren",
    delete: "Sil",
    clearLogs: "Kayıtları Temizle",
    viewChunks: "Örnek Parçalar",
    selectAll: "Tümünü Seç",
    clearSelection: "Seçimi Temizle",
    bulkReprocess: "Seçilenleri Yeniden İşle",
    bulkDelete: "Seçilenleri Sil",
    onlySingleDetail: "Tekli Detay Aç",
  },
  confirms: {
    deleteDocument: "Bu belgeyi silmek istediğinizden emin misiniz?",
    deleteSelectedDocuments: (count: number) => `${count} belge silinecek. Devam etmek istiyor musunuz?`,
    reprocessSelectedDocuments: (count: number) =>
      `${count} belge için yeniden işleme başlatılacak. Devam etmek istiyor musunuz?`,
    deleteConversation: "Bu konuşmayı silmek istediğinizden emin misiniz?",
    retryFailedJobs: "Hatalı işleri yeniden başlatmak istiyor musunuz?",
    clearLogs: "Seçili filtreye göre kayıtlar temizlenecek. Devam etmek istiyor musunuz?",
  },
  empty: {
    documents: "Belge kaydı bulunamadı.",
    jobs: "İşleme işi kaydı bulunamadı.",
    conversations: "Konuşma kaydı bulunamadı.",
    messages: "Mesaj bulunamadı.",
    logs: "Kayıt bulunamadı.",
    chunks: "Parça özeti bulunamadı.",
    chunkSamples: "Örnek parça bulunamadı.",
  },
  hints: {
    selectDocumentForDetail: "Detay için belge seçin.",
    selectConversation: "Konuşma seçin",
    selectLogForDetail: "Detay için kayıt seçin.",
    conversationIdPrefix: (conversationId: string) => `Konuşma ID: ${conversationId}`,
    chunkDocumentId: (documentId: string) => `Belge ID: ${documentId || "-"}`,
    logsCleared: (count: number) => `${count} kayıt temizlendi.`,
  },
  defaults: {
    documentReprocessed: "Belge yeniden işlendi.",
    documentRelearnQueued: "Belge yeniden öğrenme sürecine alındı.",
    documentDeleted: "Belge silindi.",
    bulkReprocessCompleted: (count: number) => `${count} belge için yeniden işleme başlatıldı.`,
    bulkDeleteCompleted: (count: number) => `${count} belge silindi.`,
    retryCompleted: "İş tekrar denendi.",
    retryFailedCompleted: "Hatalı işler yeniden başlatıldı.",
    conversationDeleted: "Konuşma silindi.",
    chunkReprocessed: "Belge yeniden işlendi.",
    actionFailed: "İşlem sırasında hata oluştu.",
  },
} as const;

export const ADMIN_TABLE_HEADERS = {
  documents: ["Seç", "Dosya Adı", "Kaynak Türü", "MIME Türü", "Dosya Boyutu", "Parça Sayısı", "Durum", "Yüklenme Tarihi", "Aksiyonlar"],
  jobs: ["Durum", "Aşama", "Belge", "Başlangıç", "Bitiş", "Tekrar Sayısı", "Hata Mesajı", "Aksiyonlar"],
  conversations: ["Konuşma ID", "Kullanıcı ID", "Başlık", "Son Mesaj", "Oluşturulma", "Aksiyonlar"],
  logs: ["Seviye", "Bileşen", "Mesaj", "Zaman", "Bağlantı", "Aksiyonlar"],
  chunks: ["Belge ID", "Dosya Adı", "Kaynak ID", "Parça Sayısı", "Aksiyonlar"],
} as const;
