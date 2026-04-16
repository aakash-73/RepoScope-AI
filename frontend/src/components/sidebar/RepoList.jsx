import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Trash2, GitBranch, FileText, ChevronRight,
  Loader2, AlertTriangle, CheckCircle, Clock, RefreshCw,
  RefreshCcw,
} from "lucide-react";
import { listRepos, deleteRepo, retryRepoImport, syncRepo } from "../../lib/api";
import { formatDate } from "../../lib/utils";

// ── Status badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status, analysisStatus }) {
  if (status === "ready") {
    if (analysisStatus === "understood") {
      return (
        <span className="flex items-center gap-1 text-[9px] text-moss font-display font-bold">
          <span className="text-[10px]">⚡</span>
          understood
        </span>
      );
    }
    if (analysisStatus === "analyzing") {
      return (
        <span className="flex items-center gap-1 text-[9px] text-moss/70 font-display animate-pulse italic">
          <span className="text-[10px]">🧠</span>
          thinking…
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 text-[9px] text-emerald-400/80 font-display">
        <CheckCircle size={9} />
        ready
      </span>
    );
  }
  if (status === "pending") {
    return (
      <span className="flex items-center gap-1 text-[9px] text-yellow-400/80 font-display animate-pulse">
        <Clock size={9} />
        importing…
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="flex items-center gap-1 text-[9px] text-red-400/80 font-display">
        <AlertTriangle size={9} />
        failed
      </span>
    );
  }
  return null;
}

// ── Sync result toast ─────────────────────────────────────────────────────────
function SyncResult({ result }) {
  if (!result) return null;

  if (result.status === "failed") {
    return (
      <motion.div
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-2 px-2.5 py-2 rounded-lg text-[10px] font-mono border bg-red-500/8 border-red-500/20 text-red-400/80"
      >
        {result.message || "Sync failed"}
      </motion.div>
    );
  }

  const isNoChange = result.status === "no_changes";

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className={`mt-2 px-2.5 py-2 rounded-lg text-[10px] font-mono border ${isNoChange
        ? "bg-white/5 border-white/10 text-slate-500"
        : "bg-moss/8 border-moss/20 text-moss/80"
        }`}
    >
      {isNoChange ? (
        "Already up to date"
      ) : (
        <span>
          +{result.added} &nbsp;~{result.modified} &nbsp;−{result.deleted}
          {result.reanalyzed > 0 && (
            <span className="text-moss/60"> · {result.reanalyzed} re-analyzing</span>
          )}
        </span>
      )}
    </motion.div>
  );
}

export default function RepoList({
  selectedId,
  onSelect,
  refreshKey,
  analysisMap = {},
  onSyncComplete,   // called after a successful sync so GraphPage can refresh
}) {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);
  const [retrying, setRetrying] = useState(null);
  const [syncing, setSyncing] = useState(null);
  const [syncResults, setSyncResults] = useState({});  // repoId → SyncResponse

  useEffect(() => {
    load();
  }, [refreshKey]);

  async function load() {
    setLoading(true);
    try {
      const data = await listRepos();
      setRepos(data);
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(e, repoId) {
    e.stopPropagation();
    if (!confirm("Delete this repository and all its data?")) return;
    setDeleting(repoId);
    try {
      await deleteRepo(repoId);
      setRepos((prev) => prev.filter((r) => r.repo_id !== repoId));
      setSyncResults((prev) => { const n = { ...prev }; delete n[repoId]; return n; });
    } catch {
      /* silent */
    } finally {
      setDeleting(null);
    }
  }

  async function handleRetry(e, repo) {
    e.stopPropagation();
    setRetrying(repo.repo_id);
    try {
      const result = await retryRepoImport(repo.repo_id);
      setRepos((prev) =>
        prev.map((r) =>
          r.repo_id === repo.repo_id
            ? { ...r, status: result.status, file_count: result.file_count, error_message: null }
            : r
        )
      );
    } catch (err) {
      const detail = err.response?.data?.detail || "Retry failed.";
      setRepos((prev) =>
        prev.map((r) =>
          r.repo_id === repo.repo_id
            ? { ...r, status: "failed", error_message: detail }
            : r
        )
      );
    } finally {
      setRetrying(null);
    }
  }

  async function handleSync(e, repo) {
    e.stopPropagation();
    setSyncing(repo.repo_id);
    setSyncResults((prev) => { const n = { ...prev }; delete n[repo.repo_id]; return n; });

    try {
      const result = await syncRepo(repo.repo_id);

      // Update file count in local state
      setRepos((prev) =>
        prev.map((r) =>
          r.repo_id === repo.repo_id
            ? {
              ...r,
              file_count: r.file_count + result.added - result.deleted,
              last_synced_at: new Date().toISOString(),
            }
            : r
        )
      );

      // Show inline result summary
      setSyncResults((prev) => ({ ...prev, [repo.repo_id]: result }));

      // Notify GraphPage to refresh the graph if this repo is currently open
      if (result.status === "synced") {
        onSyncComplete?.(repo.repo_id, result);
      }

      // Auto-clear the result after 8 seconds
      setTimeout(() => {
        setSyncResults((prev) => {
          const n = { ...prev };
          delete n[repo.repo_id];
          return n;
        });
      }, 8000);

    } catch (err) {
      const detail = err.response?.data?.detail || err.message || "Sync failed.";
      setSyncResults((prev) => ({
        ...prev,
        [repo.repo_id]: { status: "failed", message: detail },
      }));
    } finally {
      setSyncing(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 size={18} className="text-moss animate-spin" />
      </div>
    );
  }

  if (repos.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-slate-600 text-sm">No repositories yet.</p>
        <p className="text-slate-700 text-xs mt-1">Import one to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {repos.map((repo, i) => {
        const isFailed = repo.status === "failed";
        const isPending = repo.status === "pending";
        const isReady = repo.status === "ready";
        const isRetrying = retrying === repo.repo_id;
        const isDeleting = deleting === repo.repo_id;
        const isSyncing = syncing === repo.repo_id;
        const syncResult = syncResults[repo.repo_id];

        return (
          <motion.div
            key={repo.repo_id}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            onClick={() => !isFailed && !isPending && onSelect(repo)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                !isFailed && !isPending && onSelect(repo);
              }
            }}
            className={`
              w-full text-left rounded-xl p-3 transition-all duration-150 group cursor-pointer
              ${selectedId === repo.repo_id
                ? "bg-moss/10 border border-moss/25"
                : isFailed
                  ? "bg-red-500/5 border border-red-500/20 cursor-default"
                  : isPending
                    ? "bg-yellow-500/5 border border-yellow-500/20 cursor-default"
                    : "bg-charcoal-50/50 border border-white/5 hover:border-white/10 hover:bg-charcoal-50"
              }
            `}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <p className={`text-sm font-display font-medium truncate ${selectedId === repo.repo_id
                    ? "text-moss"
                    : isFailed
                      ? "text-red-400"
                      : isPending
                        ? "text-yellow-400"
                        : "text-slate-200"
                    }`}>
                    {repo.name}
                  </p>
                  {selectedId === repo.repo_id && (
                    <ChevronRight size={12} className="text-moss flex-shrink-0" />
                  )}
                </div>
                <p className="text-xs text-slate-600 truncate">{repo.owner}</p>
              </div>

              <div className="flex items-center gap-1 flex-shrink-0">
                {/* Retry button — only for failed repos */}
                {isFailed && (
                  <button
                    onClick={(e) => handleRetry(e, repo)}
                    disabled={isRetrying}
                    title="Retry import"
                    className="p-1 rounded text-yellow-400/70 hover:text-yellow-400 transition-colors"
                  >
                    {isRetrying
                      ? <Loader2 size={12} className="animate-spin" />
                      : <RefreshCw size={12} />
                    }
                  </button>
                )}

                {/* Sync button — only for ready repos */}
                {isReady && (
                  <button
                    onClick={(e) => handleSync(e, repo)}
                    disabled={isSyncing || isDeleting}
                    title={
                      repo.last_synced_at
                        ? `Last synced ${formatDate(repo.last_synced_at)}`
                        : "Sync with GitHub"
                    }
                    className="p-1 rounded opacity-0 group-hover:opacity-100 text-slate-600 hover:text-moss transition-all"
                  >
                    {isSyncing
                      ? <Loader2 size={12} className="animate-spin text-moss" />
                      : <RefreshCcw size={12} />
                    }
                  </button>
                )}

                {/* Pending spinner */}
                {isPending && (
                  <Loader2 size={12} className="text-yellow-400/60 animate-spin" />
                )}

                {/* Delete button */}
                <button
                  onClick={(e) => handleDelete(e, repo.repo_id)}
                  disabled={isDeleting || isRetrying || isSyncing}
                  className="p-1 rounded opacity-0 group-hover:opacity-100 text-slate-600 hover:text-red-400 transition-all"
                >
                  {isDeleting
                    ? <Loader2 size={12} className="animate-spin" />
                    : <Trash2 size={12} />
                  }
                </button>
              </div>
            </div>

            {/* Error message */}
            {isFailed && repo.error_message && (
              <p className="text-[10px] text-red-400/70 mt-1.5 leading-tight line-clamp-2">
                {repo.error_message}
              </p>
            )}

            <div className="flex items-center gap-3 mt-2">
              <span className="flex items-center gap-1 text-[10px] text-slate-600">
                <GitBranch size={9} />
                {repo.branch}
              </span>
              <span className="flex items-center gap-1 text-[10px] text-slate-600">
                <FileText size={9} />
                {repo.file_count} files
              </span>
              <span className="text-[10px] text-slate-700 ml-auto">
                {formatDate(repo.imported_at)}
              </span>
            </div>

            {/* Status badge row */}
            <div className="mt-1.5">
              <StatusBadge
                status={repo.status || "ready"}
                analysisStatus={repo.analysis_status}
              />
            </div>

            {/* Sync result inline summary */}
            {syncResult && <SyncResult result={syncResult} />}

            {/* Analysis progress bar */}
            {(() => {
              const ai = analysisMap[repo.repo_id];
              if (!ai || ai.status !== "analyzing") return null;
              return (
                <div className="mt-2 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] uppercase tracking-wider text-moss/60 font-display">
                      AI understanding
                    </span>
                    <span className="text-[9px] font-mono text-moss/80">
                      {Math.round(ai.percentage ?? 0)}%
                    </span>
                  </div>
                  <div className="h-0.5 rounded-full bg-white/5 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${ai.percentage ?? 0}%` }}
                      transition={{ duration: 0.5, ease: "easeOut" }}
                      className="h-full bg-moss rounded-full shadow-[0_0_6px_rgba(134,239,172,0.5)]"
                    />
                  </div>
                </div>
              );
            })()}
          </motion.div>
        );
      })}
    </div>
  );
}