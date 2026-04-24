import React, { useState, useCallback, useRef, useEffect } from "react";
import { ReactFlowProvider } from "@xyflow/react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, AlertTriangle, Network, Loader2, RefreshCw,
  ChevronDown, ChevronUp, GitBranch, FileText, Download, Cpu,
} from "lucide-react";
import GraphCanvas from "../components/graph/GraphCanvas";
import ComponentSidebar from "../components/sidebar/ComponentSidebar";
import ImportDialog from "../components/ui/ImportDialog";
import RepoList from "../components/sidebar/RepoList";
import RepoChatPanel from "../components/chat/Repochatpanel";
import GraphExportDialog from "../components/graph/Graphexportdialog";
import LanguageLegend from "../components/graph/LanguageLegend";
import GraphSearch from "../components/graph/GraphSearch";
import { fetchGraph, reanalyzeNode } from "../lib/api";
import { useKeyboardShortcuts } from "../lib/useKeyboardShortcuts";

// Build the SSE URL from the same base as the API
const SSE_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function GraphPage() {
  const [showImport, setShowImport] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [repoListKey, setRepoListKey] = useState(0);
  const [cyclesExpanded, setCyclesExpanded] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState(null);
  const [currentFile, setCurrentFile] = useState(null);
  const [repoAnalysisMap, setRepoAnalysisMap] = useState({});
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [isBuildMode, setIsBuildMode] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [graphKey, setGraphKey] = useState(0);
  const [viewType, setViewType] = useState("structure"); // "structure" or "semantic"

  const lastClickedNodeId = useRef(null);
  const lastClickTimeRef = useRef(0);
  const graphCanvasRef = useRef(null);
  const sseRef = useRef(null);   // holds the active EventSource

  const handleExport = useCallback(async (format, scale) => {
    if (!graphCanvasRef.current) throw new Error("Graph not loaded.");
    await graphCanvasRef.current.exportGraph(format, scale, selectedRepo?.name);
  }, [selectedRepo]);

  // ── Global Keyboard Shortcuts ───────────────────────────────────────────
  useKeyboardShortcuts({
    fitView: () => graphCanvasRef.current?.fitGraph(),
    toggleSemantic: () => setViewType(v => v === "structure" ? "semantic" : "structure"),
    toggleChat: () => {
      if (selectedRepo) setChatOpen(o => !o);
    }
  });

  // ── Close any open SSE connection ──────────────────────────────────────
  const closeSSE = useCallback(() => {
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
  }, []);

  // ── Patch a single node's analysis_status inside graphData ─────────────
  // This is the key function that drives the solidification effect:
  // instead of replacing the whole graph, we surgically update one node,
  // which causes CodeNode to re-render and animate from ghost → solid.
  const patchNodeStatus = useCallback((filePath, newStatus) => {
    setGraphData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        nodes: prev.nodes.map((node) =>
          node.data.file_path === filePath
            ? { ...node, data: { ...node.data, analysis_status: newStatus } }
            : node
        ),
      };
    });
  }, []);

  // ── Open SSE stream for a repo ──────────────────────────────────────────
  const openSSE = useCallback((repoId) => {
    closeSSE();

    const es = new EventSource(
      `${SSE_BASE}/api/v1/analysis/${repoId}/stream`
    );
    sseRef.current = es;

    es.onmessage = async (evt) => {
      let msg;
      try { msg = JSON.parse(evt.data); } catch { return; }

      switch (msg.type) {

        // Initial snapshot — apply all current statuses at once so the graph
        // starts in the correct ghost/solid state before any updates arrive.
        case "snapshot": {
          setGraphData((prev) => {
            if (!prev) return prev;
            const statusMap = Object.fromEntries(
              msg.nodes.map((n) => [n.file_path, n.analysis_status])
            );
            return {
              ...prev,
              nodes: prev.nodes.map((node) => {
                const s = statusMap[node.data.file_path];
                return s !== undefined
                  ? { ...node, data: { ...node.data, analysis_status: s } }
                  : node;
              }),
            };
          });
          break;
        }

        // A single node changed status — patch just that node.
        // CodeNode's Framer Motion spring will animate the opacity/filter change.
        case "node_update": {
          patchNodeStatus(msg.file_path, msg.analysis_status);
          break;
        }

        // Progress heartbeat — update the progress bar and current-file toast.
        case "progress": {
          setCurrentFile(msg.current_file ?? null);
          setAnalysisStatus({
            repo_analysis_status: msg.repo_analysis_status,
            nodes: {
              total: msg.total,
              completed: msg.completed,
              percentage: msg.percentage,
            },
          });
          setRepoAnalysisMap((prev) => ({
            ...prev,
            [repoId]: {
              percentage: msg.percentage,
              current_file: msg.current_file ?? null,
              status: msg.repo_analysis_status,
            },
          }));
          break;
        }

        // Analysis finished — close the stream, do one clean final fetch
        // so the graph reflects every node's terminal state accurately.
        case "done": {
          closeSSE();
          setCurrentFile(null);
          setAnalysisStatus((prev) => ({
            ...prev,
            repo_analysis_status: msg.repo_analysis_status,
          }));
          setRepoAnalysisMap((prev) => ({
            ...prev,
            [repoId]: { percentage: 100, current_file: null, status: msg.repo_analysis_status },
          }));
          // Small delay so the last DB writes land before we fetch
          await new Promise((r) => setTimeout(r, 1500));
          const data = await fetchGraph(repoId, viewType);
          setGraphData(data);
          break;
        }

        default:
          break;
      }
    };

    es.onerror = () => {
      // SSE connection dropped — close cleanly; the graph stays as-is.
      closeSSE();
    };
  }, [closeSSE, patchNodeStatus]);

  // ── Select a repo ───────────────────────────────────────────────────────
  const handleSelectRepo = useCallback(async (repo) => {
    setSelectedRepo(repo);
    setSelectedNode(null);
    setGraphData(null);
    setGraphError(null);
    setGraphLoading(true);
    setCyclesExpanded(false);
    setAnalysisStatus(null);
    setCurrentFile(null);
    setChatOpen(false);
    closeSSE();

    try {
      // Fetch the initial graph based on current viewType
      const data = await fetchGraph(repo.repo_id, viewType);
      setGraphData(data);
      setGraphKey((k) => k + 1);

      // Open the SSE stream unconditionally.
      // The stream self-terminates when analysis is done/failed, so it's safe
      // to open even for repos that are already fully analyzed — the "snapshot"
      // event will fire immediately with all nodes as "done", then a "done"
      // terminal event closes the stream within ~1 second.
      openSSE(repo.repo_id);

    } catch (err) {
      setGraphError(err.response?.data?.detail || "Failed to load graph.");
    } finally {
      setGraphLoading(false);
    }
  }, [closeSSE, openSSE, viewType]);

  // ── Re-fetch graph when viewType changes ────────────────────────────────
  useEffect(() => {
    if (!selectedRepo) return;
    const refetch = async () => {
      setGraphLoading(true);
      try {
        const data = await fetchGraph(selectedRepo.repo_id, viewType);
        setGraphData(data);
        setGraphKey((k) => k + 1);
      } catch (err) {
        setGraphError("Failed to switch view.");
      } finally {
        setGraphLoading(false);
      }
    };
    refetch();
  }, [viewType, selectedRepo?.repo_id]);

  const handleLanguageColorChange = useCallback((key, newColor) => {
    setGraphData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        nodes: prev.nodes.map((node) => {
          const nodeKey = `${node.data.category}:${node.data.sub_category}`;
          if (nodeKey === key) {
            return { ...node, data: { ...node.data, node_color: newColor } };
          }
          return node;
        }),
      };
    });
  }, []);

  const handleImportSuccess = useCallback(() => {
    setRepoListKey((k) => k + 1);
  }, []);

  const handleSyncComplete = useCallback(async (syncedRepoId, syncResult) => {
    // Only refresh graph if the synced repo is the one currently open
    if (syncedRepoId !== selectedRepo?.repo_id) return;

    // If files changed, re-fetch the graph so new/deleted nodes appear immediately.
    // The SSE stream will handle the solidification animation for re-analyzed nodes.
    if (syncResult.added > 0 || syncResult.deleted > 0 || syncResult.modified > 0) {
      try {
        const data = await fetchGraph(syncedRepoId, viewType);
        setGraphData(data);
        setGraphKey((k) => k + 1);  // force folder expansion reset for new/modified nodes

        // Re-open the SSE stream so the new pending nodes animate in
        openSSE(syncedRepoId);
      } catch (err) {
        console.error("Failed to refresh graph after sync:", err);
      }
    }
  }, [selectedRepo, openSSE]);

  const circularPaths = graphData?.circular_paths ?? [];
  const circularCount = circularPaths.length;

  const displayData = React.useMemo(() => graphData, [graphData]);

  const currentRepoId = selectedRepo?.repo_id ?? null;
  const isRepoOpen = !!currentRepoId && !!graphData && !graphLoading;
  const isAnalyzing = analysisStatus?.repo_analysis_status === "analyzing";

  return (
    <div className="h-full flex overflow-hidden">
      {/* ── Left sidebar ─────────────────────────────────────────────── */}
      <motion.aside
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="w-72 flex-shrink-0 flex flex-col glass rounded-none rounded-r-2xl border-r-0 overflow-hidden"
      >
        <div className="px-5 pt-5 pb-4 border-b border-white/5">
          <div className="flex items-center gap-2.5 mb-1">
            <div className="w-7 h-7 rounded-lg bg-moss flex items-center justify-center">
              <Network size={14} className="text-charcoal-300" />
            </div>
            <h1 className="font-display font-bold text-slate-100 tracking-tight">
              RepoScope AI
            </h1>
          </div>
          <p className="text-[11px] text-slate-600 font-display">
            Code Architecture Intelligence
          </p>
        </div>

        <div className="px-4 py-3 border-b border-white/5">
          <button
            onClick={() => setShowImport(true)}
            className="btn-moss w-full flex items-center justify-center gap-2 text-sm"
          >
            <Plus size={15} />
            Import Repository
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <p className="text-[10px] uppercase tracking-wider text-slate-600 font-display mb-2 px-1">
            Repositories
          </p>
          <RepoList
            selectedId={selectedRepo?.repo_id}
            onSelect={handleSelectRepo}
            refreshKey={repoListKey}
            analysisMap={repoAnalysisMap}
            onSyncComplete={handleSyncComplete}
          />
        </div>

        {graphData && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="px-4 py-4 border-t border-white/5 space-y-2"
          >
            <p className="text-[10px] uppercase tracking-wider text-slate-600 font-display mb-2">
              Graph Stats
            </p>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: "Nodes", value: graphData.nodes.length },
                { label: "Edges", value: graphData.edges.length },
              ].map(({ label, value }) => (
                <div key={label} className="glass-sm p-2 text-center">
                  <p className="text-lg font-display font-bold text-moss">{value}</p>
                  <p className="text-[10px] text-slate-600">{label}</p>
                </div>
              ))}
            </div>

            {circularCount > 0 && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 overflow-hidden">
                <button
                  onClick={() => setCyclesExpanded((v) => !v)}
                  className="w-full flex items-center gap-2 p-2.5 text-left hover:bg-red-500/5 transition-colors"
                >
                  <AlertTriangle size={13} className="text-red-400 flex-shrink-0" />
                  <span className="text-xs text-red-400 flex-1">
                    {circularCount} circular{" "}
                    {circularCount === 1 ? "dependency" : "dependencies"}
                  </span>
                  {cyclesExpanded
                    ? <ChevronUp size={12} className="text-red-400/60" />
                    : <ChevronDown size={12} className="text-red-400/60" />}
                </button>

                {cyclesExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    className="border-t border-red-500/20 px-2.5 pb-2.5 pt-2 space-y-2 max-h-48 overflow-y-auto"
                  >
                    {circularPaths.map((cycle, i) => (
                      <div key={i} className="space-y-0.5">
                        <p className="text-[9px] uppercase tracking-wider text-red-400/60 font-display">
                          Cycle {i + 1}
                        </p>
                        <div className="flex flex-col gap-0.5">
                          {cycle.map((file, j) => (
                            <div key={j} className="flex items-center gap-1">
                              {j > 0 && (
                                <span className="text-red-400/40 text-[9px] ml-1">↳</span>
                              )}
                              <span
                                className="text-[10px] font-mono text-red-300/80 truncate"
                                title={file}
                              >
                                {file.split("/").pop()}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}
              </div>
            )}
          </motion.div>
        )}
      </motion.aside>

      {/* ── Main canvas area ─────────────────────────────────────────── */}
      <div className="flex-1 flex relative overflow-hidden">

        {/* Repo header bar */}
        <AnimatePresence>
          {selectedRepo && !graphLoading && (
            <motion.div
              key={selectedRepo.repo_id}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="absolute top-4 left-4 z-10 flex items-center gap-2.5 px-3.5 py-2 rounded-xl glass border border-white/8"
            >
              <div className="w-6 h-6 rounded-md bg-moss/15 border border-moss/20 flex items-center justify-center flex-shrink-0">
                <Network size={11} className="text-moss" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-slate-600 font-mono leading-none mb-0.5">
                  {selectedRepo.owner}
                </p>
                <p className="text-sm font-display font-semibold text-slate-200 leading-none">
                  {selectedRepo.name}
                </p>
              </div>
              <div className="w-px h-7 bg-white/8 mx-0.5" />
              <div className="flex flex-col gap-0.5">
                <span className="flex items-center gap-1 text-[10px] text-slate-600 font-mono">
                  <GitBranch size={9} />
                  {selectedRepo.branch}
                </span>
                <span className="flex items-center gap-1 text-[10px] text-slate-600 font-mono">
                  <FileText size={9} />
                  {selectedRepo.file_count} files
                </span>
              </div>
              <button
                onClick={() => setIsBuildMode(!isBuildMode)}
                title={isBuildMode ? "Show all nodes" : "Show building process"}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border transition-all text-xs font-display ${isBuildMode
                  ? "bg-moss/15 border-moss/30 text-moss"
                  : "bg-white/5 border-white/10 text-slate-500 hover:text-slate-300"
                  }`}
              >
                <Plus size={12} className={isBuildMode ? "rotate-45" : ""} />
                {isBuildMode ? "Build Mode: ON" : "Build Mode: OFF"}
              </button>
              <button
                onClick={() => setViewType(viewType === "structure" ? "semantic" : "structure")}
                title={viewType === "structure" ? "Switch to Semantic View" : "Switch to Structure View"}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border transition-all text-xs font-display ${viewType === "semantic"
                  ? "bg-blue-500/15 border-blue-500/30 text-blue-400"
                  : "bg-white/5 border-white/10 text-slate-500 hover:text-slate-300"
                  }`}
              >
                <div className="relative">
                  <Network size={12} className={viewType === "semantic" ? "text-blue-400" : ""} />
                  {viewType === "semantic" && <div className="absolute -top-1 -right-1 w-2 h-2 bg-blue-400 rounded-full animate-pulse" />}
                </div>
                {viewType === "semantic" ? "Semantic View" : "Structure View"}
              </button>
              <button
                onClick={() => setShowExport(true)}
                title="Export graph"
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-moss/15 hover:border-moss/30 text-slate-500 hover:text-moss transition-all text-xs font-display"
              >
                <Download size={12} />
                Export
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Per-file toast — top right */}
        <AnimatePresence>
          {currentFile && isAnalyzing && (
            <motion.div
              key={currentFile}
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 24 }}
              transition={{ duration: 0.25 }}
              className="absolute top-4 right-4 z-20 flex items-center gap-2.5 px-3 py-2 rounded-xl glass border border-moss/25 shadow-[0_4px_20px_rgba(0,0,0,0.5)] max-w-[260px]"
            >
              <span className="relative flex-shrink-0">
                <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-moss opacity-60" />
                <Cpu size={13} className="relative text-moss" />
              </span>
              <div className="min-w-0">
                <p className="text-[9px] uppercase tracking-[0.15em] text-moss/70 font-display leading-none mb-0.5">
                  Analysing
                </p>
                <p className="text-[11px] font-mono text-slate-300 truncate leading-none" title={currentFile}>
                  {currentFile.split("/").pop()}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Progress bar — bottom centre */}
        <AnimatePresence>
          {analysisStatus && isAnalyzing && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="absolute bottom-10 left-1/2 -translate-x-1/2 z-10 w-80 glass p-4 border border-moss/30 rounded-2xl shadow-[0_8px_32px_rgba(0,0,0,0.4)] space-y-3"
            >
              <div className="flex justify-between items-center text-[10px] font-display font-bold uppercase tracking-[0.2em] text-moss">
                <div className="flex items-center gap-2">
                  <span className="text-sm">🧠</span>
                  AI Understanding
                </div>
                <span className="bg-moss/10 px-2 py-0.5 rounded-full border border-moss/20">
                  {Math.round(analysisStatus.nodes?.percentage || 0)}%
                </span>
              </div>
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden p-[1px]">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${analysisStatus.nodes?.percentage || 0}%` }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                  className="h-full bg-moss shadow-[0_0_15px_rgba(134,239,172,0.4)] rounded-full"
                />
              </div>
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-[9px] text-moss/50 font-display uppercase tracking-wider flex-shrink-0">
                  {analysisStatus.nodes?.completed ?? 0}/{analysisStatus.nodes?.total ?? 0} files
                </span>
                {currentFile && (
                  <>
                    <span className="text-slate-700 text-[9px]">·</span>
                    <p className="text-[10px] font-mono text-slate-500 truncate" title={currentFile}>
                      {currentFile.split("/").pop()}
                    </p>
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading overlay */}
        {graphLoading && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-charcoal-300/60 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-3">
              <div className="w-12 h-12 rounded-full border-2 border-moss/20 flex items-center justify-center">
                <Loader2 size={20} className="text-moss animate-spin" />
              </div>
              <p className="text-sm font-display text-slate-400">
                Analysing architecture…
              </p>
            </div>
          </div>
        )}

        {/* Error state */}
        {graphError && (
          <div className="absolute inset-0 z-20 flex items-center justify-center p-8">
            <div className="glass max-w-sm w-full p-6 text-center space-y-3">
              <AlertTriangle size={32} className="text-red-400 mx-auto" />
              <p className="font-display font-semibold text-slate-200">Failed to load graph</p>
              <p className="text-sm text-slate-500">{graphError}</p>
              <button
                onClick={() => selectedRepo && handleSelectRepo(selectedRepo)}
                className="btn-ghost flex items-center gap-2 mx-auto"
              >
                <RefreshCw size={13} />
                Retry
              </button>
            </div>
          </div>
        )}

        {graphData && (
          <GraphSearch
            nodes={graphData.nodes}
            onHighlight={(matchSet) => graphCanvasRef.current?.highlightNodes(matchSet)}
            onJumpTo={(nodeId) => graphCanvasRef.current?.jumpToNode(nodeId)}
          />
        )}

        <ReactFlowProvider>
          <LanguageLegend repoId={currentRepoId} isRepoOpen={isRepoOpen} />
          <GraphCanvas
            ref={graphCanvasRef}
            className={viewType === "semantic" ? "view-semantic" : ""}
            graphData={displayData}
            graphKey={graphKey}
            isAnalyzing={isAnalyzing}
            repoName={selectedRepo?.name}
            isChatOpen={chatOpen}
            onChatOpen={() => {
              setChatOpen(true);
              setSelectedNode(null);        // close sidebar
              lastClickedNodeId.current = null;
            }}
            onNodeClick={(node) => {
              const now = Date.now();
              const isSameNode =
                lastClickedNodeId.current === node.id && selectedNode?.id === node.id;
              const isRecent = now - (lastClickTimeRef.current || 0) < 300;

              if (isSameNode && isRecent) {
                const s = node.data.analysis_status;
                if (s !== "done" && s !== "analyzing") {
                  reanalyzeNode(selectedRepo.repo_id, node.data.file_path).catch(console.error);
                  setSidebarRefreshKey((k) => k + 1);
                }
              }
              setChatOpen(false);
              setSelectedNode(node);
              lastClickedNodeId.current = node.id;
              lastClickTimeRef.current = now;
            }}
          />
        </ReactFlowProvider>

        {selectedNode && (
          <ComponentSidebar
            node={selectedNode}
            repoId={selectedRepo?.repo_id}
            graphData={graphData}
            refreshKey={sidebarRefreshKey}
            onClose={() => {
              setSelectedNode(null);
              lastClickedNodeId.current = null;
            }}
            onJumpTo={(nodeId) => graphCanvasRef.current?.jumpToNode(nodeId)}
          />
        )}

        <RepoChatPanel
          open={chatOpen}
          onClose={() => setChatOpen(false)}
          repoId={selectedRepo?.repo_id}
          repoName={selectedRepo?.name}
        />
      </div>

      <AnimatePresence>
        {showExport && (
          <GraphExportDialog
            repoName={selectedRepo?.name}
            onExport={handleExport}
            onClose={() => setShowExport(false)}
          />
        )}
      </AnimatePresence>

      {showImport && (
        <ImportDialog
          onClose={() => setShowImport(false)}
          onSuccess={handleImportSuccess}
        />
      )}
    </div>
  );
}