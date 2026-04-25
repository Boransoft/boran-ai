import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import TopBar from "../components/TopBar";
import {
  ADMIN_TABLE_HEADERS,
  ADMIN_TAB_LABELS,
  ADMIN_TEXTS,
  toAdminComponentLabel,
  toAdminLogLevelLabel,
  toAdminRoleLabel,
  toAdminSourceTypeLabel,
  toAdminStageLabel,
  toAdminStatusLabel,
} from "../constants/adminTexts";
import {
  bulkDeleteAdminDocuments,
  bulkReprocessAdminDocuments,
  clearAdminLogs,
  deleteAdminConversation,
  deleteAdminDocument,
  fetchAdminChunkSamples,
  fetchAdminChunkSummary,
  fetchAdminConversationMessages,
  fetchAdminConversations,
  fetchAdminDashboard,
  fetchAdminDocumentDetail,
  fetchAdminDocuments,
  fetchAdminIngestJobs,
  fetchAdminLogDetail,
  fetchAdminLogs,
  reprocessAdminDocument,
  retryAdminIngestJob,
  retryFailedAdminIngestJobs,
} from "../services/adminService";
import { useAuthStore } from "../store/authStore";
import { useMessageStore } from "../store/messageStore";
import { clearSessionCacheForUser, CLEAR_PERSISTED_MESSAGES_ON_LOGOUT_DEFAULT } from "../store/persistence";
import { useUploadStore } from "../store/uploadStore";
import type {
  AdminChunkSampleItem,
  AdminChunkSummaryItem,
  AdminConversationItem,
  AdminConversationMessageItem,
  AdminDashboardResponse,
  AdminDocumentDetailResponse,
  AdminDocumentItem,
  AdminIngestJobItem,
  AdminLogDetailResponse,
  AdminLogItem,
  AdminRelatedRefs,
} from "../types/admin";
import { formatDateTime, truncate } from "../utils/format";

type AdminTab = "dashboard" | "documents" | "jobs" | "conversations" | "logs" | "chunks";
type NoticeTone = "success" | "error" | "info";

const TABS: Array<{ key: AdminTab; label: string }> = [
  { key: "dashboard", label: ADMIN_TAB_LABELS.dashboard },
  { key: "documents", label: ADMIN_TAB_LABELS.documents },
  { key: "jobs", label: ADMIN_TAB_LABELS.jobs },
  { key: "conversations", label: ADMIN_TAB_LABELS.conversations },
  { key: "logs", label: ADMIN_TAB_LABELS.logs },
  { key: "chunks", label: ADMIN_TAB_LABELS.chunks },
];

const ADMIN_UI_REVISION = "ADMIN_UI_REV: checkbox_v1";

function statusBadge(status: string): string {
  const value = status.trim().toLowerCase();
  if (["error", "failed", "failure", "critical"].includes(value)) return "bg-rose-500/20 text-rose-300 border-rose-400/30";
  if (["running", "processing", "active"].includes(value)) return "bg-amber-500/20 text-amber-200 border-amber-400/30";
  if (["queued", "pending", "waiting"].includes(value)) return "bg-sky-500/20 text-sky-200 border-sky-400/30";
  if (["ok", "ready", "success", "completed", "retried"].includes(value)) return "bg-emerald-500/20 text-emerald-200 border-emerald-400/30";
  return "bg-slate-700/50 text-slate-200 border-slate-500/40";
}

function formatBytes(value: number): string {
  if (!value || value <= 0) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(size >= 100 ? 0 : 1)} ${units[index]}`;
}

function noticeClass(tone: NoticeTone): string {
  if (tone === "success") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
  if (tone === "error") return "border-rose-500/40 bg-rose-500/10 text-rose-200";
  return "border-sky-500/40 bg-sky-500/10 text-sky-200";
}

function compactTags(tags: string | string[]): string {
  return Array.isArray(tags) ? tags.join(", ") : (tags || "-");
}

function isFailedStatus(value: string): boolean {
  const status = value.trim().toLowerCase();
  return status === "failed" || status === "error";
}

type TableProps = {
  headers: readonly ReactNode[];
  children: ReactNode;
  containerClassName?: string;
  tableClassName?: string;
  headCellClassName?: string;
  colGroup?: ReactNode;
};

function AdminTable({
  headers,
  children,
  containerClassName,
  tableClassName,
  headCellClassName,
  colGroup,
}: TableProps) {
  const containerClass = `overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/70 ${containerClassName || ""}`;
  const tableClass = `min-w-full text-left text-xs text-slate-200 sm:text-sm ${tableClassName || ""}`;
  const headerClass = headCellClassName || "whitespace-nowrap px-3 py-2.5 font-semibold";
  return (
    <div className={containerClass.trim()}>
      <table className={tableClass.trim()}>
        {colGroup}
        <thead className="bg-slate-900/80 text-[11px] uppercase tracking-wide text-slate-400 sm:text-xs">
          <tr>
            {headers.map((header, index) => (
              <th key={typeof header === "string" ? header : `header-${index}`} className={headerClass}>
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function EmptyRow({ colSpan, message }: { colSpan: number; message: string }) {
  return (
    <tr className="border-t border-slate-800">
      <td colSpan={colSpan} className="px-3 py-5 text-center text-slate-400">
        {message}
      </td>
    </tr>
  );
}

function InlineActionButton({
  label,
  onClick,
  disabled,
  tone = "default",
  size = "default",
  className,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  tone?: "default" | "danger";
  size?: "default" | "compact";
  className?: string;
}) {
  const base = "inline-flex items-center justify-center rounded-md border font-medium transition disabled:cursor-not-allowed disabled:opacity-60";
  const sizeClass = size === "compact"
    ? "min-h-6 px-2 py-0.5 text-[10px] leading-4"
    : "px-2 py-1 text-[11px]";
  const toneClass = tone === "danger"
    ? "border-rose-500/50 text-rose-200 hover:border-rose-400 hover:text-rose-100"
    : "border-slate-600 text-slate-200 hover:border-slate-400 hover:text-white";
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`${base} ${sizeClass} ${toneClass} ${className || ""}`}>
      {label}
    </button>
  );
}

export default function AdminPage() {
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const clearActiveUserUploadCache = useUploadStore((state) => state.clearActiveUserCache);
  const clearActiveUserMessageCache = useMessageStore((state) => state.clearActiveUserCache);

  const currentUserExternalId = user?.external_id || null;
  const [activeTab, setActiveTab] = useState<AdminTab>("dashboard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState<{ tone: NoticeTone; message: string } | null>(null);
  const [busyActionKey, setBusyActionKey] = useState("");

  const [dashboard, setDashboard] = useState<AdminDashboardResponse | null>(null);
  const [docStatus, setDocStatus] = useState("");
  const [docQuery, setDocQuery] = useState("");
  const [documents, setDocuments] = useState<AdminDocumentItem[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<AdminDocumentItem | null>(null);
  const [selectedDocumentDetail, setSelectedDocumentDetail] = useState<AdminDocumentDetailResponse | null>(null);

  const [jobStatus, setJobStatus] = useState("");
  const [jobs, setJobs] = useState<AdminIngestJobItem[]>([]);
  const [selectedJob, setSelectedJob] = useState<AdminIngestJobItem | null>(null);

  const [conversations, setConversations] = useState<AdminConversationItem[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState("");
  const [conversationMessages, setConversationMessages] = useState<AdminConversationMessageItem[]>([]);

  const [logLevel, setLogLevel] = useState("");
  const [logComponent, setLogComponent] = useState("");
  const [logs, setLogs] = useState<AdminLogItem[]>([]);
  const [selectedLogDetail, setSelectedLogDetail] = useState<AdminLogDetailResponse | null>(null);

  const [chunkSummary, setChunkSummary] = useState<AdminChunkSummaryItem[]>([]);
  const [chunkTotal, setChunkTotal] = useState(0);
  const [selectedChunkDocumentId, setSelectedChunkDocumentId] = useState("");
  const [chunkSamples, setChunkSamples] = useState<AdminChunkSampleItem[]>([]);

  const runLogoutCleanup = useCallback(() => {
    clearSessionCacheForUser(currentUserExternalId);
    clearActiveUserUploadCache();
    clearActiveUserMessageCache({
      clearPersisted: CLEAR_PERSISTED_MESSAGES_ON_LOGOUT_DEFAULT,
    });
    clearAuth();
  }, [clearActiveUserMessageCache, clearActiveUserUploadCache, clearAuth, currentUserExternalId]);

  const runLoad = useCallback(
    async (work: () => Promise<void>) => {
      if (!token) return;
      setLoading(true);
      setError("");
      try {
        await work();
      } catch (err) {
        const detail = err instanceof Error ? err.message : ADMIN_TEXTS.loadError;
        setError(detail);
      } finally {
        setLoading(false);
      }
    },
    [token],
  );

  const runAction = useCallback(
    async (key: string, work: () => Promise<string>) => {
      if (!token) return;
      setBusyActionKey(key);
      setNotice(null);
      try {
        const message = await work();
        setNotice({ tone: "success", message });
      } catch (err) {
        const detail = err instanceof Error ? err.message : ADMIN_TEXTS.defaults.actionFailed;
        setNotice({ tone: "error", message: detail });
      } finally {
        setBusyActionKey("");
      }
    },
    [token],
  );

  const getDocumentRowId = useCallback((item: AdminDocumentItem) => {
    return (item.document_id || item.id || "").trim();
  }, []);

  const loadDashboard = useCallback(async () => {
    if (!token) return;
    const result = await fetchAdminDashboard(token);
    setDashboard(result);
  }, [token]);

  const loadDocuments = useCallback(async () => {
    if (!token) return;
    const result = await fetchAdminDocuments({ token, status: docStatus, q: docQuery, limit: 100, offset: 0 });
    setDocuments(result.items);
  }, [docQuery, docStatus, token]);

  const loadJobs = useCallback(async () => {
    if (!token) return;
    const result = await fetchAdminIngestJobs({ token, status: jobStatus, limit: 100, offset: 0 });
    setJobs(result.items);
  }, [jobStatus, token]);

  const loadConversations = useCallback(async () => {
    if (!token) return;
    const result = await fetchAdminConversations({ token, limit: 80, offset: 0 });
    setConversations(result.items);
  }, [token]);

  const loadConversationMessages = useCallback(async (conversationId: string, limit = 16) => {
    if (!token || !conversationId) return;
    const result = await fetchAdminConversationMessages({ token, conversationId, limit });
    setConversationMessages(result.items);
  }, [token]);

  const loadLogs = useCallback(async () => {
    if (!token) return;
    const result = await fetchAdminLogs({ token, level: logLevel, component: logComponent, limit: 120, offset: 0 });
    setLogs(result.items);
  }, [logComponent, logLevel, token]);

  const loadChunkSummary = useCallback(async () => {
    if (!token) return;
    const result = await fetchAdminChunkSummary({ token, limit: 120 });
    setChunkSummary(result.items);
    setChunkTotal(result.total_chunks);
  }, [token]);

  const refreshAllAdminViews = useCallback(async () => {
    await Promise.all([loadDashboard(), loadDocuments(), loadJobs(), loadConversations(), loadLogs(), loadChunkSummary()]);
  }, [loadChunkSummary, loadConversations, loadDashboard, loadDocuments, loadJobs, loadLogs]);

  const openDocumentDetail = useCallback(async (item: AdminDocumentItem) => {
    if (!token) return;
    setSelectedDocument(item);
    const detail = await fetchAdminDocumentDetail({ token, documentId: item.document_id || item.id });
    setSelectedDocumentDetail(detail);
  }, [token]);

  const openConversation = useCallback((conversationId: string) => {
    setSelectedConversationId(conversationId);
    void runLoad(async () => {
      await loadConversationMessages(conversationId);
    });
  }, [loadConversationMessages, runLoad]);

  const openLogDetail = useCallback(async (logId: string) => {
    if (!token) return;
    const detail = await fetchAdminLogDetail({ token, logId });
    setSelectedLogDetail(detail);
  }, [token]);

  const loadChunkSampleList = useCallback(async (documentId: string) => {
    if (!token) return;
    const result = await fetchAdminChunkSamples({ token, documentId, limit: 8 });
    setSelectedChunkDocumentId(documentId);
    setChunkSamples(result.items);
  }, [token]);

  const jumpToDocuments = useCallback((query = "", status = "") => {
    setDocQuery(query);
    setDocStatus(status);
    setActiveTab("documents");
  }, []);

  const jumpToJobs = useCallback((status = "") => {
    setJobStatus(status);
    setActiveTab("jobs");
  }, []);

  const jumpToConversations = useCallback(() => {
    setActiveTab("conversations");
  }, []);

  const jumpToLogs = useCallback((level = "") => {
    setLogLevel(level);
    setActiveTab("logs");
  }, []);

  const jumpByLogRefs = useCallback((refs: AdminRelatedRefs | undefined) => {
    if (!refs) return;
    if (refs.document_id) {
      jumpToDocuments(refs.document_id);
      return;
    }
    if (refs.job_id) {
      jumpToJobs();
      return;
    }
    if (refs.conversation_id) {
      setSelectedConversationId(refs.conversation_id);
      jumpToConversations();
    }
  }, [jumpToConversations, jumpToDocuments, jumpToJobs]);

  const refreshCurrent = useCallback(() => {
    if (activeTab === "dashboard") {
      void runLoad(loadDashboard);
      return;
    }
    if (activeTab === "documents") {
      void runLoad(loadDocuments);
      return;
    }
    if (activeTab === "jobs") {
      void runLoad(loadJobs);
      return;
    }
    if (activeTab === "conversations") {
      void runLoad(loadConversations);
      return;
    }
    if (activeTab === "logs") {
      void runLoad(loadLogs);
      return;
    }
    void runLoad(loadChunkSummary);
  }, [activeTab, loadChunkSummary, loadConversations, loadDashboard, loadDocuments, loadJobs, loadLogs, runLoad]);

  useEffect(() => {
    void runLoad(loadDashboard);
  }, [loadDashboard, runLoad]);

  useEffect(() => {
    if (activeTab === "documents") {
      void runLoad(loadDocuments);
      return;
    }
    if (activeTab === "jobs") {
      void runLoad(loadJobs);
      return;
    }
    if (activeTab === "conversations") {
      void runLoad(loadConversations);
      return;
    }
    if (activeTab === "logs") {
      void runLoad(loadLogs);
      return;
    }
    if (activeTab === "chunks") {
      void runLoad(loadChunkSummary);
    }
  }, [activeTab, loadChunkSummary, loadConversations, loadDocuments, loadJobs, loadLogs, runLoad]);

  useEffect(() => {
    const visibleIds = new Set(documents.map((item) => getDocumentRowId(item)).filter((item) => item.length > 0));
    setSelectedDocumentIds((previous) => previous.filter((item) => visibleIds.has(item)));
  }, [documents, getDocumentRowId]);

  const recentErrorCount = useMemo(() => dashboard?.recent_errors?.length || 0, [dashboard?.recent_errors]);
  const visibleDocumentIds = useMemo(
    () => documents.map((item) => getDocumentRowId(item)).filter((item) => item.length > 0),
    [documents, getDocumentRowId],
  );
  const selectedDocumentCount = selectedDocumentIds.length;
  const allVisibleSelected = visibleDocumentIds.length > 0 && visibleDocumentIds.every((id) => selectedDocumentIds.includes(id));

  const toggleDocumentSelection = useCallback((documentId: string, checked: boolean) => {
    setSelectedDocumentIds((previous) => {
      if (checked) {
        if (previous.includes(documentId)) {
          return previous;
        }
        return [...previous, documentId];
      }
      return previous.filter((item) => item !== documentId);
    });
  }, []);

  const toggleSelectAllVisibleDocuments = useCallback((checked: boolean) => {
    if (checked) {
      setSelectedDocumentIds(visibleDocumentIds);
      return;
    }
    setSelectedDocumentIds([]);
  }, [visibleDocumentIds]);

  const clearSelectedDocuments = useCallback(() => {
    setSelectedDocumentIds([]);
  }, []);

  const bulkDeleteSelectedDocuments = useCallback(() => {
    if (!token) {
      return;
    }
    if (selectedDocumentCount === 0) {
      return;
    }
    if (!window.confirm(ADMIN_TEXTS.confirms.deleteSelectedDocuments(selectedDocumentCount))) {
      return;
    }
    void runAction("documents:bulk-delete", async () => {
      const response = await bulkDeleteAdminDocuments({ token, documentIds: selectedDocumentIds });
      const deletedCount = Number(response.deleted ?? 0);
      const failures = Array.isArray(response.failures) ? response.failures.length : 0;
      clearSelectedDocuments();
      if (selectedDocument && selectedDocumentIds.includes(getDocumentRowId(selectedDocument))) {
        setSelectedDocument(null);
        setSelectedDocumentDetail(null);
      }
      await refreshAllAdminViews();
      if (failures > 0) {
        throw new Error(`${deletedCount} belge silindi, ${failures} belge silinemedi.`);
      }
      return `${deletedCount} belge silindi.`;
    });
  }, [
    clearSelectedDocuments,
    getDocumentRowId,
    refreshAllAdminViews,
    runAction,
    selectedDocument,
    selectedDocumentCount,
    selectedDocumentIds,
    token,
  ]);

  const bulkReprocessSelectedDocuments = useCallback(() => {
    if (!token) {
      return;
    }
    if (selectedDocumentCount === 0) {
      return;
    }
    if (!window.confirm(ADMIN_TEXTS.confirms.reprocessSelectedDocuments(selectedDocumentCount))) {
      return;
    }
    void runAction("documents:bulk-reprocess", async () => {
      const response = await bulkReprocessAdminDocuments({ token, documentIds: selectedDocumentIds });
      const startedCount = Number(response.started ?? 0);
      const failures = Array.isArray(response.failures) ? response.failures.length : 0;
      await refreshAllAdminViews();
      if (failures > 0) {
        throw new Error(`${startedCount} belge için işlem başlatıldı, ${failures} belge başlatılamadı.`);
      }
      return ADMIN_TEXTS.defaults.bulkReprocessCompleted(startedCount);
    });
  }, [refreshAllAdminViews, runAction, selectedDocumentCount, selectedDocumentIds, token]);

  const documentHeaders = useMemo<readonly ReactNode[]>(() => {
    const [, ...rest] = ADMIN_TABLE_HEADERS.documents;
    return [
      <label className="flex items-center justify-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-slate-200" key="select-all">
        <input
          type="checkbox"
          checked={allVisibleSelected}
          onChange={(event) => toggleSelectAllVisibleDocuments(event.target.checked)}
          className="h-3.5 w-3.5 cursor-pointer rounded border border-slate-400 bg-slate-900 accent-cyan-500 focus:ring-cyan-500"
          aria-label={ADMIN_TEXTS.actions.selectAll}
        />
        <span className="hidden normal-case text-[10px] text-slate-300 xl:inline">{ADMIN_TEXTS.actions.selectAll}</span>
      </label>,
      ...rest,
    ];
  }, [allVisibleSelected, toggleSelectAllVisibleDocuments]);

  if (!token) {
    return null;
  }

  return (
    <div className="relative flex h-[100dvh] min-h-[100svh] flex-col overflow-hidden bg-slate-950 text-slate-100">
      <TopBar user={user} onLogout={runLogoutCleanup} adminMode showAdminSwitch={Boolean(user?.is_admin)} />
      <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col overflow-hidden px-3 pb-3 pt-3 sm:px-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold text-white sm:text-xl">{ADMIN_TEXTS.pageTitle}</h1>
            <p className="text-xs text-slate-400 sm:text-sm">{ADMIN_TEXTS.pageSubtitle}</p>
            <p className="mt-1 text-[11px] font-medium text-cyan-300">{ADMIN_UI_REVISION}</p>
          </div>
          <button
            type="button"
            onClick={refreshCurrent}
            disabled={loading}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 transition hover:border-slate-500 hover:text-white disabled:opacity-60"
          >
            {loading ? ADMIN_TEXTS.loading : ADMIN_TEXTS.refresh}
          </button>
        </div>

        <div className="mb-3 flex flex-wrap gap-2">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium sm:text-sm ${
                activeTab === tab.key
                  ? "border-cyan-400/60 bg-cyan-400/20 text-cyan-100"
                  : "border-slate-700 bg-slate-900/70 text-slate-300 hover:border-slate-500 hover:text-slate-100"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {error ? <p className="mb-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">{error}</p> : null}
        {notice ? <p className={`mb-3 rounded-lg border px-3 py-2 text-xs ${noticeClass(notice.tone)}`}>{notice.message}</p> : null}

        <section className="flex-1 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900/35 p-3 sm:p-4">
          {activeTab === "dashboard" ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-2 lg:grid-cols-6">
                <button type="button" onClick={() => jumpToDocuments()} className="rounded-xl border border-slate-700 bg-slate-900/70 p-3 text-left transition hover:border-cyan-500/60">
                  <p className="text-[11px] text-slate-400">{ADMIN_TEXTS.metrics.totalDocuments}</p>
                  <p className="mt-1 text-xl font-semibold">{dashboard?.counts.documents ?? "-"}</p>
                </button>
                <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-3">
                  <p className="text-[11px] text-slate-400">{ADMIN_TEXTS.metrics.totalUsers}</p>
                  <p className="mt-1 text-xl font-semibold">{dashboard?.counts.users ?? "-"}</p>
                </div>
                <button type="button" onClick={() => setActiveTab("chunks")} className="rounded-xl border border-slate-700 bg-slate-900/70 p-3 text-left transition hover:border-cyan-500/60">
                  <p className="text-[11px] text-slate-400">{ADMIN_TEXTS.metrics.totalChunks}</p>
                  <p className="mt-1 text-xl font-semibold">{dashboard?.counts.chunks ?? "-"}</p>
                </button>
                <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-3">
                  <p className="text-[11px] text-slate-400">{ADMIN_TEXTS.metrics.activeJobs}</p>
                  <p className="mt-1 text-xl font-semibold">{dashboard?.counts.ingest_active ?? "-"}</p>
                </div>
                <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-3">
                  <p className="text-[11px] text-slate-400">{ADMIN_TEXTS.metrics.queuedJobs}</p>
                  <p className="mt-1 text-xl font-semibold">{dashboard?.counts.ingest_pending ?? "-"}</p>
                </div>
                <button type="button" onClick={() => jumpToJobs("failed")} className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-left transition hover:border-rose-400/60">
                  <p className="text-[11px] text-rose-200">{ADMIN_TEXTS.metrics.failedJobs}</p>
                  <p className="mt-1 text-xl font-semibold text-rose-100">{dashboard?.counts.ingest_failed ?? "-"}</p>
                </button>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-white">{ADMIN_TEXTS.metrics.recentErrors} ({recentErrorCount})</p>
                    <InlineActionButton label={ADMIN_TEXTS.actions.goToLogs} onClick={() => jumpToLogs("ERROR")} />
                  </div>
                  <div className="space-y-2 text-xs">
                    {(dashboard?.recent_errors || []).length === 0 ? (
                      <p className="text-slate-400">{ADMIN_TEXTS.noData}</p>
                    ) : (
                      dashboard?.recent_errors.map((item) => (
                        <div key={item.id} className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-2">
                          <p className="text-rose-200">{truncate(item.message, 130)}</p>
                          <p className="mt-1 text-[11px] text-slate-400">{toAdminLogLevelLabel(item.level)} | {toAdminComponentLabel(item.component)} | {formatDateTime(item.timestamp)}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-white">{ADMIN_TEXTS.metrics.recentConversations}</p>
                    <InlineActionButton label={ADMIN_TEXTS.actions.goToConversations} onClick={jumpToConversations} />
                  </div>
                  <div className="space-y-2 text-xs">
                    {(dashboard?.recent_conversations || []).length === 0 ? (
                      <p className="text-slate-400">{ADMIN_TEXTS.noData}</p>
                    ) : (
                      dashboard?.recent_conversations.map((item) => (
                        <button key={item.conversation_id} type="button" onClick={() => { setActiveTab("conversations"); setSelectedConversationId(item.conversation_id); }} className="w-full rounded-lg border border-slate-700 bg-slate-900/70 p-2 text-left transition hover:border-cyan-500/60">
                          <p className="text-slate-100">{truncate(item.title || item.conversation_id, 90)}</p>
                          <p className="mt-1 text-[11px] text-slate-400">{item.user_id || "-"} | {formatDateTime(item.last_message_at)}</p>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-white">{ADMIN_TEXTS.metrics.recentDocuments}</p>
                  <InlineActionButton label={ADMIN_TEXTS.actions.goToDocuments} onClick={() => jumpToDocuments()} />
                </div>
                <div className="space-y-2 text-xs">
                  {(dashboard?.recent_documents || []).length === 0 ? (
                    <p className="text-slate-400">{ADMIN_TEXTS.noData}</p>
                  ) : (
                    dashboard?.recent_documents.map((item) => (
                      <button key={item.id} type="button" onClick={() => { setActiveTab("documents"); setDocQuery(item.document_id); }} className="w-full rounded-lg border border-slate-700 bg-slate-900/70 p-2 text-left transition hover:border-cyan-500/60">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-slate-100">{truncate(item.file_name || item.document_id, 90)}</p>
                          <span className={`rounded-md border px-2 py-0.5 text-[11px] ${statusBadge(item.status)}`}>{toAdminStatusLabel(item.status)}</span>
                        </div>
                        <p className="mt-1 text-[11px] text-slate-400">{ADMIN_TEXTS.fields.chunk}: {item.chunk_count} | {formatDateTime(item.uploaded_at)}</p>
                      </button>
                    ))
                  )}
                </div>
              </div>

              {dashboard && dashboard.missing_tables.length > 0 ? (
                <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">{ADMIN_TEXTS.missingTablesPrefix} {dashboard.missing_tables.join(", ")}</p>
              ) : null}
            </div>
          ) : null}

          {activeTab === "documents" ? (
            <div className="grid gap-2.5 xl:grid-cols-[minmax(0,1.75fr)_minmax(320px,0.95fr)]">
              <div className="space-y-2.5">
                <div className="grid items-center gap-2 sm:grid-cols-[minmax(0,1fr)_170px_auto]">
                  <input value={docQuery} onChange={(event) => setDocQuery(event.target.value)} placeholder={ADMIN_TEXTS.filters.fileSearch} className="h-8 rounded-lg border border-slate-700 bg-slate-950 px-2.5 text-xs text-slate-100 outline-none ring-cyan-400 focus:ring" />
                  <select value={docStatus} onChange={(event) => setDocStatus(event.target.value)} className="h-8 rounded-lg border border-slate-700 bg-slate-950 px-2.5 text-xs text-slate-100 outline-none ring-cyan-400 focus:ring">
                    <option value="">{ADMIN_TEXTS.filters.allStatuses}</option>
                    <option value="ready">{toAdminStatusLabel("ready")}</option>
                    <option value="queued">{toAdminStatusLabel("queued")}</option>
                    <option value="processing">{toAdminStatusLabel("processing")}</option>
                    <option value="error">{toAdminStatusLabel("error")}</option>
                    <option value="failed">{toAdminStatusLabel("failed")}</option>
                  </select>
                  <button type="button" onClick={() => void runLoad(loadDocuments)} className="h-8 rounded-lg border border-slate-700 bg-slate-900 px-3 text-xs text-slate-200 hover:border-slate-500">{ADMIN_TEXTS.actions.applyFilter}</button>
                </div>

                {selectedDocumentCount > 0 ? (
                  <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1">
                    <p className="text-[11px] text-cyan-100">{ADMIN_TEXTS.selectedCount(selectedDocumentCount)}</p>
                    <div className="flex flex-wrap gap-1">
                      <InlineActionButton label={ADMIN_TEXTS.actions.bulkReprocess} size="compact" disabled={busyActionKey === "documents:bulk-reprocess"} onClick={bulkReprocessSelectedDocuments} />
                      <InlineActionButton label={ADMIN_TEXTS.actions.bulkDelete} size="compact" tone="danger" disabled={busyActionKey === "documents:bulk-delete"} onClick={bulkDeleteSelectedDocuments} />
                      <InlineActionButton label={ADMIN_TEXTS.actions.clearSelection} size="compact" onClick={clearSelectedDocuments} />
                    </div>
                  </div>
                ) : null}

                <AdminTable
                  headers={documentHeaders}
                  containerClassName="rounded-lg border-slate-800/90"
                  tableClassName="table-fixed min-w-[1140px] text-[12px] sm:text-[12px]"
                  headCellClassName="whitespace-nowrap px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400"
                  colGroup={(
                    <colgroup>
                      <col style={{ width: "44px" }} />
                      <col style={{ width: "30%" }} />
                      <col style={{ width: "9%" }} />
                      <col style={{ width: "10%" }} />
                      <col style={{ width: "7%" }} />
                      <col style={{ width: "6%" }} />
                      <col style={{ width: "8%" }} />
                      <col style={{ width: "12%" }} />
                      <col style={{ width: "200px" }} />
                    </colgroup>
                  )}
                >
                  {documents.length === 0 ? (
                    <EmptyRow colSpan={9} message={ADMIN_TEXTS.empty.documents} />
                  ) : (
                    documents.map((item) => {
                      const rowId = getDocumentRowId(item);
                      const busyPrefix = `doc:${rowId}`;
                      const busy = busyActionKey.startsWith(busyPrefix);
                      const isSelected = selectedDocumentIds.includes(rowId);
                      return (
                        <tr key={item.id} className={`border-t border-slate-800/80 transition-colors ${isSelected ? "bg-cyan-500/10 hover:bg-cyan-500/15" : "hover:bg-slate-900/55"}`}>
                          <td className="px-2 py-1 align-middle">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(event) => toggleDocumentSelection(rowId, event.target.checked)}
                              className="h-3.5 w-3.5 cursor-pointer rounded border border-slate-400 bg-slate-900 accent-cyan-500 focus:ring-cyan-500"
                              aria-label={`belge-sec-${rowId}`}
                            />
                          </td>
                          <td className="px-2 py-1 align-middle">
                            <p title={item.file_name || item.document_id} className="overflow-hidden text-ellipsis [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2] leading-4 text-slate-100">
                              {item.file_name || item.document_id}
                            </p>
                          </td>
                          <td className="px-2 py-1 align-middle text-[11px] text-slate-300">{toAdminSourceTypeLabel(item.source_type || "-")}</td>
                          <td className="px-2 py-1 align-middle">
                            <span className="block truncate text-[11px] text-slate-300" title={item.mime_type || "-"}>
                              {item.mime_type || "-"}
                            </span>
                          </td>
                          <td className="px-2 py-1 align-middle text-right text-[11px] tabular-nums text-slate-300">{formatBytes(item.file_size)}</td>
                          <td className="px-2 py-1 align-middle text-center text-[11px] tabular-nums text-slate-300">{item.chunk_count}</td>
                          <td className="px-2 py-1 align-middle">
                            <span className={`inline-flex rounded-md border px-1.5 py-0.5 text-[10px] font-medium ${statusBadge(item.status)}`}>{toAdminStatusLabel(item.status)}</span>
                          </td>
                          <td className="px-2 py-1 align-middle text-[11px] leading-4 text-slate-300">{formatDateTime(item.uploaded_at)}</td>
                          <td className="px-2 py-1 align-middle">
                            <div className="grid grid-cols-2 gap-1">
                              <InlineActionButton size="compact" className="w-full whitespace-nowrap" label={ADMIN_TEXTS.actions.openDetail} onClick={() => { void runLoad(async () => { await openDocumentDetail(item); }); }} />
                              <InlineActionButton size="compact" className="w-full whitespace-nowrap" label={ADMIN_TEXTS.actions.reprocess} disabled={busy} onClick={() => { void runAction(`${busyPrefix}:reprocess`, async () => { const response = await reprocessAdminDocument({ token, documentId: rowId }); await refreshAllAdminViews(); return String(response.message || ADMIN_TEXTS.defaults.documentReprocessed); }); }} />
                              <InlineActionButton size="compact" className="w-full whitespace-nowrap" label={ADMIN_TEXTS.actions.relearn} disabled={busy} onClick={() => { void runAction(`${busyPrefix}:relearn`, async () => { const response = await reprocessAdminDocument({ token, documentId: rowId }); await refreshAllAdminViews(); return String(response.message || ADMIN_TEXTS.defaults.documentRelearnQueued); }); }} />
                              <InlineActionButton size="compact" className="w-full whitespace-nowrap" label={ADMIN_TEXTS.actions.delete} tone="danger" disabled={busy} onClick={() => {
                                if (!window.confirm(ADMIN_TEXTS.confirms.deleteDocument)) return;
                                void runAction(`${busyPrefix}:delete`, async () => {
                                  const response = await deleteAdminDocument({ token, documentId: rowId });
                                  setSelectedDocumentIds((previous) => previous.filter((id) => id !== rowId));
                                  if ((selectedDocument?.document_id || selectedDocument?.id) === rowId) {
                                    setSelectedDocument(null);
                                    setSelectedDocumentDetail(null);
                                  }
                                  await refreshAllAdminViews();
                                  return String(response.message || ADMIN_TEXTS.defaults.documentDeleted);
                                });
                              }} />
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </AdminTable>
              </div>

              <div className="h-fit rounded-xl border border-slate-800 bg-slate-950/70 p-3 xl:sticky xl:top-3">
                <p className="mb-2 text-sm font-semibold text-white">{ADMIN_TEXTS.panels.documentDetail}</p>
                {!selectedDocument ? (
                  <div className="flex min-h-[240px] items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-900/30 px-4">
                    <p className="text-center text-xs text-slate-400">{ADMIN_TEXTS.hints.selectDocumentForDetail}</p>
                  </div>
                ) : null}
                {selectedDocument ? (
                  <div className="max-h-[calc(100dvh-240px)] space-y-3 overflow-y-auto pr-1 text-xs">
                    <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-2.5">
                      <p className="text-[11px] uppercase tracking-wide text-slate-400">{ADMIN_TEXTS.fields.document}</p>
                      <p className="mt-1 break-words text-sm font-medium text-slate-100">{selectedDocument.file_name || "-"}</p>
                      <p className="mt-1 text-[11px] text-slate-400">
                        {ADMIN_TEXTS.fields.documentId}: <span className="text-slate-300">{selectedDocument.document_id || "-"}</span>
                      </p>
                    </div>
                    <dl className="grid grid-cols-[110px_1fr] gap-x-3 gap-y-1.5 text-[11px] leading-5">
                      <dt className="text-slate-400">{ADMIN_TEXTS.fields.userId}</dt>
                      <dd className="break-all text-slate-200">{selectedDocument.user_id || "-"}</dd>
                      <dt className="text-slate-400">{ADMIN_TEXTS.fields.status}</dt>
                      <dd className="text-slate-200">{toAdminStatusLabel(selectedDocument.status)}</dd>
                      <dt className="text-slate-400">{ADMIN_TEXTS.fields.category}</dt>
                      <dd className="text-slate-200">{selectedDocument.category || "-"}</dd>
                      <dt className="text-slate-400">{ADMIN_TEXTS.fields.tags}</dt>
                      <dd className="break-words text-slate-200">{compactTags(selectedDocument.tags)}</dd>
                      <dt className="text-slate-400">{ADMIN_TEXTS.fields.source}</dt>
                      <dd className="break-words text-slate-200">{selectedDocumentDetail?.source || "-"}</dd>
                    </dl>
                    <div className="rounded-lg border border-slate-800 bg-slate-900/45 p-2.5">
                      <p className="text-[11px] text-slate-400">{ADMIN_TEXTS.fields.filePath}</p>
                      <p className="mt-1 break-all text-[11px] text-slate-300">{selectedDocumentDetail?.file_path || "-"}</p>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}
          {activeTab === "jobs" ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <select value={jobStatus} onChange={(event) => setJobStatus(event.target.value)} className="h-9 rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-100 outline-none ring-cyan-400 focus:ring sm:text-sm">
                  <option value="">{ADMIN_TEXTS.filters.allStatuses}</option>
                  <option value="running">{toAdminStatusLabel("running")}</option>
                  <option value="queued">{toAdminStatusLabel("queued")}</option>
                  <option value="ready">{toAdminStatusLabel("ready")}</option>
                  <option value="error">{toAdminStatusLabel("error")}</option>
                  <option value="failed">{toAdminStatusLabel("failed")}</option>
                </select>
                <button type="button" onClick={() => void runLoad(loadJobs)} className="h-9 rounded-lg border border-slate-700 bg-slate-900 px-3 text-xs text-slate-200 hover:border-slate-500 sm:text-sm">{ADMIN_TEXTS.actions.applyFilter}</button>
                <button type="button" onClick={() => {
                  if (!window.confirm(ADMIN_TEXTS.confirms.retryFailedJobs)) return;
                  void runAction("jobs:retry-failed", async () => {
                    const response = await retryFailedAdminIngestJobs({ token, limit: 20 });
                    await refreshAllAdminViews();
                    return String(response.message || ADMIN_TEXTS.defaults.retryFailedCompleted);
                  });
                }} className="h-9 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 text-xs text-amber-200 hover:border-amber-400 sm:text-sm">{ADMIN_TEXTS.actions.retryFailed}</button>
              </div>

              <AdminTable headers={ADMIN_TABLE_HEADERS.jobs}>
                {jobs.length === 0 ? (
                  <EmptyRow colSpan={8} message={ADMIN_TEXTS.empty.jobs} />
                ) : (
                  jobs.map((item) => {
                    const failed = isFailedStatus(item.status);
                    const rowKey = item.id || `${item.document_id}:${item.started_at}`;
                    const busy = busyActionKey.startsWith(`job:${rowKey}`);
                    return (
                      <tr key={rowKey} className={`border-t border-slate-800 ${failed ? "bg-rose-500/5" : ""}`}>
                        <td className="px-3 py-2.5"><span className={`rounded-md border px-2 py-0.5 text-[11px] ${statusBadge(item.status)}`}>{toAdminStatusLabel(item.status)}</span></td>
                        <td className="px-3 py-2.5">{toAdminStageLabel(item.stage || "-")}</td>
                        <td className="px-3 py-2.5"><p>{truncate(item.file_name || item.document_id || "-", 30)}</p><p className="text-[11px] text-slate-500">{truncate(item.document_id || "-", 24)}</p></td>
                        <td className="px-3 py-2.5">{formatDateTime(item.started_at)}</td>
                        <td className="px-3 py-2.5">{formatDateTime(item.completed_at)}</td>
                        <td className="px-3 py-2.5">{item.retry_count ?? 0}</td>
                        <td className="px-3 py-2.5 text-rose-200">{truncate(item.error_message || "-", 80)}</td>
                        <td className="px-3 py-2.5">
                          <div className="flex flex-wrap gap-1.5">
                            <InlineActionButton label={ADMIN_TEXTS.actions.openDetail} onClick={() => setSelectedJob(item)} />
                            {failed ? (
                              <InlineActionButton label={ADMIN_TEXTS.actions.retry} disabled={busy} onClick={() => {
                                void runAction(`job:${rowKey}:retry`, async () => {
                                  const response = await retryAdminIngestJob({ token, jobId: item.id });
                                  await refreshAllAdminViews();
                                  return String(response.message || ADMIN_TEXTS.defaults.retryCompleted);
                                });
                              }} />
                            ) : null}
                            {item.document_id ? <InlineActionButton label={ADMIN_TEXTS.actions.goToDocument} onClick={() => jumpToDocuments(item.document_id)} /> : null}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </AdminTable>

              {selectedJob ? (
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-xs">
                  <p className="mb-2 text-sm font-semibold text-white">{ADMIN_TEXTS.panels.jobDetail}</p>
                  <p><span className="text-slate-400">{ADMIN_TEXTS.fields.jobId}:</span> {selectedJob.id || "-"}</p>
                  <p><span className="text-slate-400">{ADMIN_TEXTS.fields.document}:</span> {selectedJob.file_name || "-"}</p>
                  <p><span className="text-slate-400">{ADMIN_TEXTS.fields.documentId}:</span> {selectedJob.document_id || "-"}</p>
                  <p><span className="text-slate-400">{ADMIN_TEXTS.fields.status}:</span> {toAdminStatusLabel(selectedJob.status)}</p>
                  <p><span className="text-slate-400">{ADMIN_TEXTS.fields.retryCount}:</span> {selectedJob.retry_count ?? 0}</p>
                  <p className="text-rose-200"><span className="text-slate-400">{ADMIN_TEXTS.fields.errorMessage}:</span> {selectedJob.error_message || "-"}</p>
                </div>
              ) : null}
            </div>
          ) : null}

          {activeTab === "conversations" ? (
            <div className="grid gap-3 lg:grid-cols-[1.3fr_1fr]">
              <div className="space-y-2">
                <AdminTable headers={ADMIN_TABLE_HEADERS.conversations}>
                  {conversations.length === 0 ? (
                    <EmptyRow colSpan={6} message={ADMIN_TEXTS.empty.conversations} />
                  ) : (
                    conversations.map((item) => {
                      const busy = busyActionKey.startsWith(`conversation:${item.conversation_id}`);
                      return (
                        <tr key={item.conversation_id} className="border-t border-slate-800">
                          <td className="px-3 py-2.5">{truncate(item.conversation_id, 20)}</td>
                          <td className="px-3 py-2.5">{truncate(item.user_id || "-", 20)}</td>
                          <td className="px-3 py-2.5">{truncate(item.title || "-", 40)}</td>
                          <td className="px-3 py-2.5">{formatDateTime(item.last_message_at)}</td>
                          <td className="px-3 py-2.5">{formatDateTime(item.created_at)}</td>
                          <td className="px-3 py-2.5">
                            <div className="flex flex-wrap gap-1.5">
                              <InlineActionButton label={ADMIN_TEXTS.actions.open} onClick={() => openConversation(item.conversation_id)} />
                              <InlineActionButton label={ADMIN_TEXTS.actions.showRecentMessages} onClick={() => {
                                setSelectedConversationId(item.conversation_id);
                                void runLoad(async () => {
                                  await loadConversationMessages(item.conversation_id, 24);
                                });
                              }} />
                              <InlineActionButton label={ADMIN_TEXTS.actions.userDocuments} onClick={() => jumpToDocuments(item.user_id || "")} />
                              <InlineActionButton label={ADMIN_TEXTS.actions.delete} tone="danger" disabled={busy} onClick={() => {
                                if (!window.confirm(ADMIN_TEXTS.confirms.deleteConversation)) return;
                                void runAction(`conversation:${item.conversation_id}:delete`, async () => {
                                  const response = await deleteAdminConversation({ token, conversationId: item.conversation_id });
                                  if (selectedConversationId === item.conversation_id) {
                                    setSelectedConversationId("");
                                    setConversationMessages([]);
                                  }
                                  await Promise.all([loadConversations(), loadDashboard()]);
                                  return String(response.message || ADMIN_TEXTS.defaults.conversationDeleted);
                                });
                              }} />
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </AdminTable>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">
                <p className="mb-2 text-sm font-semibold text-white">{ADMIN_TEXTS.panels.conversationDetail}</p>
                <p className="mb-2 text-xs text-slate-400">{selectedConversationId ? ADMIN_TEXTS.hints.conversationIdPrefix(selectedConversationId) : ADMIN_TEXTS.hints.selectConversation}</p>
                <div className="space-y-2">
                  {conversationMessages.length === 0 ? (
                    <p className="text-xs text-slate-400">{ADMIN_TEXTS.empty.messages}</p>
                  ) : (
                    conversationMessages.map((message) => (
                      <div key={message.id} className="rounded-lg border border-slate-700 bg-slate-900/70 p-2 text-xs">
                        <p className="text-[11px] uppercase tracking-wide text-slate-400">{toAdminRoleLabel(message.role || "message")} | {formatDateTime(message.created_at)}</p>
                        <p className="mt-1 whitespace-pre-wrap text-slate-100">{truncate(message.content || "-", 500)}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : null}

          {activeTab === "logs" ? (
            <div className="grid gap-3 xl:grid-cols-[1.4fr_1fr]">
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <select value={logLevel} onChange={(event) => setLogLevel(event.target.value)} className="h-9 rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-100 outline-none ring-cyan-400 focus:ring sm:text-sm">
                    <option value="">{ADMIN_TEXTS.filters.allLevels}</option>
                    <option value="ERROR">{toAdminLogLevelLabel("ERROR")}</option>
                    <option value="CRITICAL">{toAdminLogLevelLabel("CRITICAL")}</option>
                    <option value="WARNING">{toAdminLogLevelLabel("WARNING")}</option>
                    <option value="INFO">{toAdminLogLevelLabel("INFO")}</option>
                  </select>
                  <input value={logComponent} onChange={(event) => setLogComponent(event.target.value)} placeholder={ADMIN_TEXTS.filters.componentSearch} className="h-9 min-w-[220px] flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 text-xs text-slate-100 outline-none ring-cyan-400 focus:ring sm:text-sm" />
                  <button type="button" onClick={() => void runLoad(loadLogs)} className="h-9 rounded-lg border border-slate-700 bg-slate-900 px-3 text-xs text-slate-200 hover:border-slate-500 sm:text-sm">{ADMIN_TEXTS.actions.applyFilter}</button>
                  <button type="button" onClick={() => {
                    setLogLevel("");
                    setLogComponent("");
                    setSelectedLogDetail(null);
                    void runLoad(async () => {
                      if (!token) return;
                      const result = await fetchAdminLogs({ token, level: "", component: "", limit: 120, offset: 0 });
                      setLogs(result.items);
                    });
                  }} className="h-9 rounded-lg border border-slate-700 bg-slate-900 px-3 text-xs text-slate-200 hover:border-slate-500 sm:text-sm">{ADMIN_TEXTS.actions.clearFilter}</button>
                  <button type="button" onClick={() => {
                    if (!window.confirm(ADMIN_TEXTS.confirms.clearLogs)) return;
                    void runAction("logs:clear", async () => {
                      const response = await clearAdminLogs({ token, level: logLevel, component: logComponent });
                      await refreshAllAdminViews();
                      return String(response.message || ADMIN_TEXTS.hints.logsCleared(Number(response.cleared ?? 0)));
                    });
                  }} className="h-9 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 text-xs text-rose-200 hover:border-rose-400 sm:text-sm">{ADMIN_TEXTS.actions.clearLogs}</button>
                </div>

                <AdminTable headers={ADMIN_TABLE_HEADERS.logs}>
                  {logs.length === 0 ? (
                    <EmptyRow colSpan={6} message={ADMIN_TEXTS.empty.logs} />
                  ) : (
                    logs.map((item) => (
                      <tr key={item.id} className="border-t border-slate-800">
                        <td className="px-3 py-2.5"><span className={`rounded-md border px-2 py-0.5 text-[11px] ${statusBadge(item.level)}`}>{toAdminLogLevelLabel(item.level)}</span></td>
                        <td className="px-3 py-2.5">{toAdminComponentLabel(item.component || "-")}</td>
                        <td className="px-3 py-2.5 text-slate-200">{truncate(item.message || "-", 140)}</td>
                        <td className="px-3 py-2.5">{formatDateTime(item.timestamp)}</td>
                        <td className="px-3 py-2.5">
                          <div className="flex flex-wrap gap-1">
                            {item.related?.document_id ? <InlineActionButton label={ADMIN_TEXTS.labels.relatedDocument} onClick={() => jumpToDocuments(item.related?.document_id || "")} /> : null}
                            {item.related?.conversation_id ? <InlineActionButton label={ADMIN_TEXTS.labels.relatedConversation} onClick={() => { setSelectedConversationId(item.related?.conversation_id || ""); jumpToConversations(); }} /> : null}
                            {item.related?.job_id ? <InlineActionButton label={ADMIN_TEXTS.labels.relatedJob} onClick={() => jumpToJobs()} /> : null}
                          </div>
                        </td>
                        <td className="px-3 py-2.5"><InlineActionButton label={ADMIN_TEXTS.actions.openDetail} onClick={() => { void runLoad(async () => { await openLogDetail(item.id); }); }} /></td>
                      </tr>
                    ))
                  )}
                </AdminTable>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-xs">
                <p className="mb-2 text-sm font-semibold text-white">{ADMIN_TEXTS.panels.logDetail}</p>
                {!selectedLogDetail ? <p className="text-slate-400">{ADMIN_TEXTS.hints.selectLogForDetail}</p> : null}
                {selectedLogDetail ? (
                  <div className="space-y-2">
                    <p><span className="text-slate-400">{ADMIN_TEXTS.fields.level}:</span> {toAdminLogLevelLabel(selectedLogDetail.level)}</p>
                    <p><span className="text-slate-400">{ADMIN_TEXTS.fields.component}:</span> {toAdminComponentLabel(selectedLogDetail.component)}</p>
                    <p><span className="text-slate-400">{ADMIN_TEXTS.fields.time}:</span> {formatDateTime(selectedLogDetail.timestamp)}</p>
                    <p className="whitespace-pre-wrap text-slate-100">{selectedLogDetail.message}</p>
                    {selectedLogDetail.related ? (
                      <div className="space-y-1 text-[11px] text-slate-300">
                        <p className="text-slate-400">{ADMIN_TEXTS.panels.relatedRecords}:</p>
                        {selectedLogDetail.related.document_id ? <p>{ADMIN_TEXTS.fields.documentId}: {selectedLogDetail.related.document_id}</p> : null}
                        {selectedLogDetail.related.job_id ? <p>{ADMIN_TEXTS.fields.jobId}: {selectedLogDetail.related.job_id}</p> : null}
                        {selectedLogDetail.related.conversation_id ? <p>{ADMIN_TEXTS.fields.conversationId}: {selectedLogDetail.related.conversation_id}</p> : null}
                        <div><InlineActionButton label={ADMIN_TEXTS.actions.goToRelatedRecord} onClick={() => jumpByLogRefs(selectedLogDetail.related)} /></div>
                      </div>
                    ) : null}
                    <details className="rounded-lg border border-slate-700 bg-slate-900/70 p-2">
                      <summary className="cursor-pointer text-slate-300">{ADMIN_TEXTS.panels.rawLogRecord}</summary>
                      <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-[11px] text-slate-300">{JSON.stringify(selectedLogDetail.raw, null, 2)}</pre>
                    </details>
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}

          {activeTab === "chunks" ? (
            <div className="grid gap-3 xl:grid-cols-[1.4fr_1fr]">
              <div className="space-y-3">
                <p className="text-xs text-slate-400">{ADMIN_TEXTS.metrics.totalChunksLabel}: {chunkTotal}</p>
                <AdminTable headers={ADMIN_TABLE_HEADERS.chunks}>
                  {chunkSummary.length === 0 ? (
                    <EmptyRow colSpan={5} message={ADMIN_TEXTS.empty.chunks} />
                  ) : (
                    chunkSummary.map((item) => {
                      const busy = busyActionKey.startsWith(`chunk:${item.document_id}`);
                      return (
                        <tr key={`${item.document_id}:${item.source_id}`} className="border-t border-slate-800">
                          <td className="px-3 py-2.5">{truncate(item.document_id || "-", 22)}</td>
                          <td className="px-3 py-2.5">{truncate(item.file_name || "-", 52)}</td>
                          <td className="px-3 py-2.5">{truncate(item.source_id || "-", 18)}</td>
                          <td className="px-3 py-2.5">{item.chunk_count}</td>
                          <td className="px-3 py-2.5">
                            <div className="flex flex-wrap gap-1.5">
                              <InlineActionButton label={ADMIN_TEXTS.actions.goToDocument} onClick={() => jumpToDocuments(item.document_id)} />
                              <InlineActionButton label={ADMIN_TEXTS.actions.viewChunks} onClick={() => { void runLoad(async () => { await loadChunkSampleList(item.document_id); }); }} />
                              <InlineActionButton label={ADMIN_TEXTS.actions.reprocess} disabled={busy} onClick={() => {
                                void runAction(`chunk:${item.document_id}:reprocess`, async () => {
                                  const response = await reprocessAdminDocument({ token, documentId: item.document_id });
                                  await refreshAllAdminViews();
                                  return String(response.message || ADMIN_TEXTS.defaults.chunkReprocessed);
                                });
                              }} />
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </AdminTable>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-xs">
                <p className="mb-2 text-sm font-semibold text-white">{ADMIN_TEXTS.panels.chunkSamples}</p>
                <p className="mb-2 text-slate-400">{ADMIN_TEXTS.hints.chunkDocumentId(selectedChunkDocumentId)}</p>
                {chunkSamples.length === 0 ? (
                  <p className="text-slate-400">{ADMIN_TEXTS.empty.chunkSamples}</p>
                ) : (
                  <div className="space-y-2">
                    {chunkSamples.map((sample) => (
                      <div key={`${selectedChunkDocumentId}:${sample.chunk_index}`} className="rounded-lg border border-slate-700 bg-slate-900/70 p-2">
                        <p className="text-[11px] text-slate-400">{ADMIN_TEXTS.fields.chunk} #{sample.chunk_index}</p>
                        <p className="mt-1 whitespace-pre-wrap text-slate-100">{truncate(sample.content || "-", 360)}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
