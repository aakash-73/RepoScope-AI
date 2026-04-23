import React, {
  useState, useCallback, useEffect, useRef as useReactRef, forwardRef, useImperativeHandle,
} from "react";
import {
  ReactFlow, Background, Controls, MiniMap, Panel, BackgroundVariant,
  useNodesState, useEdgesState, useReactFlow,
} from "@xyflow/react";
import { toPng, toSvg } from "html-to-image";
import { MessageCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import "@xyflow/react/dist/style.css";
import CodeNode from "./CodeNode";
import FolderGroup from "./FolderGroup";
import FlowEdge from "./FlowEdge";
import { applyDagreLayout } from "../../lib/graph-layout";
import { applyForceLayout } from "../../lib/force-layout";
import { getLanguageColor } from "../../lib/utils";

const nodeTypes = { codeNode: CodeNode, folderGroup: FolderGroup, hubNode: CodeNode };
const edgeTypes = { flowEdge: FlowEdge };

function prepareEdges(rawEdges, rawNodes) {
  const nodeMap = {};
  (rawNodes || []).forEach((n) => { nodeMap[n.id] = n.data; });

  return rawEdges.map((e) => {
    const srcData = nodeMap[e.source];
    const tgtData = nodeMap[e.target];
    const isPending =
      srcData?.analysis_status === "pending" || tgtData?.analysis_status === "pending";

    const isSemanticGraph = rawNodes?.length > 0 && rawNodes[0].data?.isSemantic === true;

    return {
      ...e,
      type: "flowEdge",
      data: {
        ...(e.data ?? {}),
        is_circular: e.is_circular ?? false,
        coupling_score: e.coupling_score ?? 0,
        cross_folder: (srcData?.folder || ".") !== (tgtData?.folder || "."),
        is_pending: isPending,
        dimmed: false,
        isSemantic: isSemanticGraph, // Explicitly tag edges with the graph type
      },
    };
  });
}

function computeDeadIds(rawNodes, rawEdges) {
  const hasIncoming = new Set(rawEdges.map((e) => e.target));
  return new Set(
    rawNodes
      .filter((n) => n.type === "codeNode" && !hasIncoming.has(n.id))
      .map((n) => n.id)
  );
}

function computeComplexityScores(rawNodes, rawEdges) {
  const importCount = {};
  const dependentCount = {};
  rawNodes.forEach((n) => { importCount[n.id] = 0; dependentCount[n.id] = 0; });
  rawEdges.forEach((e) => {
    if (importCount[e.source] !== undefined) importCount[e.source]++;
    if (dependentCount[e.target] !== undefined) dependentCount[e.target]++;
  });

  const scores = {};
  rawNodes.forEach((n) => {
    if (n.type !== "codeNode") return;
    const lines = n.data?.lines || 0;
    const imps = importCount[n.id] || 0;
    const deps = dependentCount[n.id] || 0;

    const linesScore = Math.min(lines / 600, 1);
    const impsScore = Math.min(imps / 20, 1);
    const depsScore = Math.min(deps / 15, 1);

    const raw = depsScore * 0.45 + linesScore * 0.35 + impsScore * 0.2;
    scores[n.id] = Math.max(1, Math.round(raw * 9) + 1);
  });
  return scores;
}

function buildTransitiveChains(nodeId, rawEdges) {
  const imports = {};
  const importedBy = {};
  rawEdges.forEach((e) => {
    if (!imports[e.source]) imports[e.source] = [];
    if (!importedBy[e.target]) importedBy[e.target] = [];
    imports[e.source].push(e.target);
    importedBy[e.target].push(e.source);
  });

  function traverse(start, graph) {
    const visited = new Set();
    const queue = [start];
    while (queue.length) {
      const cur = queue.shift();
      (graph[cur] || []).forEach((nb) => {
        if (!visited.has(nb)) { visited.add(nb); queue.push(nb); }
      });
    }
    return visited;
  }

  return {
    upstreamIds: traverse(nodeId, importedBy),
    downstreamIds: traverse(nodeId, imports),
  };
}

const GraphCanvasInner = forwardRef(function GraphCanvasInner(
  { graphData, graphKey, onNodeClick, isAnalyzing, onChatOpen, isChatOpen, repoName, className },
  ref
) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { fitView, getViewport, setViewport } = useReactFlow();
  const [collapsedFolders, setCollapsedFolders] = useState(new Set());
  const taggedRef = useReactRef({ nodes: [], edges: [] });

  // ── FIX: track whether initial folder state has been set for this repo ──
  // Without this, every SSE node_update patch triggers graphData to change,
  // which re-runs the tagging effect, which resets collapsedFolders — wiping
  // out any manual expand/collapse the user just did.
  const initialFoldersSetRef = useReactRef(false);

  const handleToggleCollapse = useCallback((folder) => {
    setCollapsedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folder)) next.delete(folder);
      else next.add(folder);

      // Persist to localStorage so the state survives refreshes
      if (graphData?.repo_id) {
        const key = `collapsed_folders_${graphData.repo_id}`;
        localStorage.setItem(key, JSON.stringify(Array.from(next)));
      }
      return next;
    });
  }, [graphData?.repo_id]);

  // ── FIX: reset the "folders initialised" flag only when repo changes ───
  // graphData.repo_id changes when a different repo is selected but NOT when
  // SSE patches update individual node statuses — so this correctly resets
  // the flag for new repos without resetting it on every patch.
  useEffect(() => {
    initialFoldersSetRef.current = false;
  }, [graphData?.repo_id, graphKey]);

  // ── Tag nodes + set initial folder collapse state ─────────────────────
  useEffect(() => {
    if (!graphData) return;

    const deadIds = computeDeadIds(graphData.nodes, graphData.edges);
    const complexScores = computeComplexityScores(graphData.nodes, graphData.edges);
    const circularNodeIds = new Set(
      (graphData.circular_paths ?? []).flatMap((cycle) => cycle)
    );
    const circularEdgePairs = new Set(
      (graphData.circular_paths ?? []).flatMap((cycle) =>
        cycle.slice(0, -1).map((node, i) => `${node}→${cycle[i + 1]}`)
      )
    );

    taggedRef.current.nodes = graphData.nodes.map((n) => ({
      ...n,
      data: {
        ...n.data,
        isSemantic: graphData.is_semantic,
        is_dead: n.type === "codeNode" ? deadIds.has(n.id) : false,
        complexity_score: n.type === "codeNode" ? (complexScores[n.id] ?? 1) : 1,
        is_circular: n.type === "codeNode" ? (n.data?.is_circular || circularNodeIds.has(n.data?.file_path)) : false,
      },
    }));

    taggedRef.current.edges = graphData.edges.map((e) => {
      const srcPath = graphData.nodes.find((n) => n.id === e.source)?.data?.file_path;
      const tgtPath = graphData.nodes.find((n) => n.id === e.target)?.data?.file_path;
      const derivedCircular =
        srcPath && tgtPath ? circularEdgePairs.has(`${srcPath}→${tgtPath}`) : false;
      return { ...e, is_circular: e.is_circular || derivedCircular };
    });

    // ── FIX: only set collapsedFolders on the first load of this repo ────
    // Persistence: load from localStorage if available, otherwise default to expanded.
    if (!initialFoldersSetRef.current) {
      initialFoldersSetRef.current = true;

      const repoId = graphData?.repo_id;
      const key = `collapsed_folders_${repoId}`;
      const saved = repoId ? localStorage.getItem(key) : null;

      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setCollapsedFolders(new Set(parsed));
          return;
        } catch (err) {
          console.error("Failed to parse saved expansion state:", err);
        }
      }

      // Default: Keep everything expanded (empty Set) so the user 
      // sees the full architecture by default.
      setCollapsedFolders(new Set());
    } else {
      // SSE patch — collapsedFolders didn't change so the layout effect won't
      // fire. Surgically push the updated analysis_status values into the live
      // ReactFlow nodes so CodeNode re-renders and animates (ghost → solid /
      // pulse). We only touch nodes whose status actually changed to avoid
      // unnecessary re-renders.
      setNodes((prev) =>
        prev.map((node) => {
          if (node.type !== "codeNode") return node;
          const src = taggedRef.current.nodes.find((n) => n.id === node.id);
          if (!src) return node;
          const newStatus = src.data.analysis_status;
          if (node.data.analysis_status === newStatus) return node;
          return { ...node, data: { ...node.data, analysis_status: newStatus } };
        })
      );
    }
  }, [graphData, isAnalyzing]);

  // ── Re-run layout when collapsed state changes ────────────────────────
  // FIX: graphData removed from this dependency array. Previously having
  // graphData here caused the layout to re-run (and fitView to fire) on
  // every SSE patch, resetting the user's manual pan/zoom. The tagging
  // effect above keeps taggedRef in sync with graphData — the layout effect
  // only needs to react to collapsedFolders and handleToggleCollapse.
  useEffect(() => {
    if (!taggedRef.current.nodes.length) return;
    
    let ln, le;
    if (graphData.is_semantic) {
      const result = applyForceLayout(
        taggedRef.current.nodes,
        taggedRef.current.edges
      );
      ln = result.nodes;
      le = result.edges;
    } else {
      const result = applyDagreLayout(
        taggedRef.current.nodes,
        taggedRef.current.edges,
        collapsedFolders
      );
      ln = result.nodes;
      le = result.edges;
    }
    const withCallbacks = ln.map((n) =>
      n.type === "folderGroup"
        ? { ...n, data: { ...n.data, onToggleCollapse: handleToggleCollapse } }
        : n
    );
    setNodes(withCallbacks);
    setEdges(prepareEdges(le, withCallbacks));
    setTimeout(() => fitView({ padding: 0.12, duration: 600 }), 100);
  }, [collapsedFolders, handleToggleCollapse]);

  const handleNodeMouseEnter = useCallback((_, node) => {
    if (node.type !== "codeNode") return;

    setEdges((eds) => {
      const edgeSnapshot = eds.map((e) => ({ id: e.id, source: e.source, target: e.target }));
      const { upstreamIds, downstreamIds } = buildTransitiveChains(node.id, edgeSnapshot);
      const chainNodeIds = new Set([node.id, ...upstreamIds, ...downstreamIds]);

      setNodes((nds) =>
        nds.map((n) => {
          if (n.type !== "codeNode") return n;
          const inChain = chainNodeIds.has(n.id);
          return {
            ...n,
            style: {
              ...n.style,
              opacity: inChain ? 1 : 0.2,
              transition: "opacity 0.15s ease",
            },
          };
        })
      );

      return eds.map((e) => {
        const isDirectUpstream = e.target === node.id;
        const isDirectDownstream = e.source === node.id;
        const isTransUpstream = !isDirectUpstream && upstreamIds.has(e.target) && upstreamIds.has(e.source);
        const isTransDownstream = !isDirectDownstream && downstreamIds.has(e.source) && downstreamIds.has(e.target);

        let chainRole = null;
        if (isDirectUpstream) chainRole = "direct-upstream";
        else if (isDirectDownstream) chainRole = "direct-downstream";
        else if (isTransUpstream) chainRole = "upstream";
        else if (isTransDownstream) chainRole = "downstream";

        return { ...e, data: { ...e.data, chainRole, hovering: true } };
      });
    });
  }, []);

  const handleNodeMouseLeave = useCallback(() => {
    setNodes((nds) =>
      nds.map((n) => {
        if (n.type !== "codeNode") return n;
        const { opacity: _o, transition: _t, ...restStyle } = n.style || {};
        return { ...n, style: restStyle };
      })
    );
    setEdges((eds) =>
      eds.map((e) => ({ ...e, data: { ...e.data, chainRole: null, hovering: false } }))
    );
  }, []);

  const handleNodeClick = useCallback(
    (_, node) => { if (node.type === "codeNode") onNodeClick?.(node); },
    [onNodeClick]
  );

  const minimapNodeColor = useCallback((node) => {
    if (node.type === "folderGroup") return "rgba(255,255,255,0.06)";
    if (node.data?.is_circular) return "#FF4500";
    if (node.data?.is_dead) return "#6B7280";
    return getLanguageColor(node.data?.language) || "#374151";
  }, []);

  useImperativeHandle(ref, () => ({
    highlightNodes(matchSet) {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.type !== "codeNode") return n;
          return {
            ...n,
            style: {
              ...n.style,
              opacity: matchSet && !matchSet.has(n.id) ? 0.15 : 1,
            },
          };
        })
      );
      setEdges((eds) =>
        eds.map((e) => ({
          ...e,
          data: {
            ...e.data,
            dimmed: matchSet
              ? !matchSet.has(e.source) && !matchSet.has(e.target)
              : false,
          },
        }))
      );
    },
    jumpToNode(nodeId) {
      setNodes((nds) => {
        const t = nds.find((n) => n.id === nodeId);
        if (t) fitView({ nodes: [t], padding: 0.5, duration: 500 });
        return nds;
      });
    },
    fitGraph() {
      fitView({ padding: 0.12, duration: 500 });
    },
    async exportGraph(format, scale, repoName) {
      if (format === "json") {
        const payload = JSON.stringify({ nodes, edges }, null, 2);
        const blob = new Blob([payload], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.download = `${repoName || "graph"}-${new Date().toISOString().slice(0, 10)}.json`;
        a.href = url;
        a.click();
        URL.revokeObjectURL(url);
        return;
      }

      if (format === "mermaid") {
        let mmd = "graph TD;\n";
        nodes.forEach((n) => {
          if (n.type === "codeNode") {
            const cleanLabel = (n.data?.label || n.id).replace(/"/g, "'");
            mmd += `  ${n.id}["${cleanLabel}"];\n`;
          }
        });
        edges.forEach((e) => {
          mmd += `  ${e.source} --> ${e.target};\n`;
        });
        const blob = new Blob([mmd], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.download = `${repoName || "graph"}-${new Date().toISOString().slice(0, 10)}.mmd`;
        a.href = url;
        a.click();
        URL.revokeObjectURL(url);
        return;
      }

      const renderer = document.querySelector(".react-flow__renderer");
      if (!renderer) throw new Error("ReactFlow renderer not found.");

      // ── 1. Save current viewport ─────────────────────────────────────
      const prev = getViewport();
      fitView({ padding: 0.06, duration: 0 });

      // Wait for ReactFlow to re-render (onlyRenderVisibleElements may
      // need to mount off-screen nodes after fitView brings them in).
      await new Promise((r) => setTimeout(r, 350));

      // ── 2. Inject export-mode CSS overrides ──────────────────────────
      //    html-to-image cannot render `backdrop-filter` or translucent
      //    backgrounds properly — they appear ghostly/washed out.  We
      //    temporarily swap ALL transparent backgrounds with SOLID, BRIGHT
      //    equivalents so the exported image looks crisp and readable.
      const exportCSS = document.createElement("style");
      exportCSS.setAttribute("data-export", "true");
      exportCSS.textContent = `
        /* ── Kill transitions + animations for perf & consistency ────── */
        .react-flow__renderer *,
        .react-flow__renderer *::before,
        .react-flow__renderer *::after {
          transition: none !important;
          animation-play-state: paused !important;
        }

        /* ── BRIGHT solid node backgrounds ──────────────────────────── */
        .react-flow__node-codeNode > div {
          background: #282828 !important;
          border: 1.5px solid rgba(255,255,255,0.35) !important;
          opacity: 1 !important;
          box-shadow: 0 4px 20px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.08) !important;
        }

        /* ── Brighter color strip at top of nodes ──────────────────── */
        .react-flow__node-codeNode > div > div:first-child {
          opacity: 1 !important;
          height: 3px !important;
        }

        /* ── BRIGHT folder group backgrounds & borders ─────────────── */
        .react-flow__node-folderGroup > div {
          background: rgba(35,35,35,0.98) !important;
          border-width: 2px !important;
          border-color: rgba(182,255,59,0.45) !important;
        }
        /* Folder header bar */
        .react-flow__node-folderGroup > div > div:first-child {
          background: rgba(50,50,50,0.95) !important;
          border: 1.5px solid rgba(182,255,59,0.4) !important;
        }
        /* Folder label text */
        .react-flow__node-folderGroup span {
          opacity: 1 !important;
        }

        /* ── BIGGER, BOLDER badges ─────────────────────────────────── */
        .react-flow__node-codeNode [class*="-top-3"] {
          transform: scale(1.4) translateY(-2px);
          transform-origin: left center;
          box-shadow: 0 3px 12px rgba(0,0,0,0.8) !important;
          z-index: 10 !important;
          font-size: 10px !important;
          font-weight: 800 !important;
          padding: 3px 7px !important;
          border: 1px solid rgba(255,255,255,0.2) !important;
        }

        /* ── BRIGHT text everywhere ────────────────────────────────── */
        .react-flow__node-codeNode p,
        .react-flow__node-codeNode span {
          opacity: 1 !important;
        }
        .react-flow__node-codeNode .text-slate-300,
        .react-flow__node-codeNode .font-mono {
          color: #f3f4f6 !important;
          font-weight: 600 !important;
        }
        .react-flow__node-codeNode .text-slate-600,
        .react-flow__node-codeNode .text-slate-500 {
          color: #d1d5db !important;
        }
        .react-flow__node-codeNode .text-\\[11px\\] {
          font-size: 12px !important;
        }
        .react-flow__node-codeNode .text-\\[10px\\] {
          font-size: 11px !important;
        }
        .react-flow__node-codeNode .text-\\[9px\\] {
          font-size: 10px !important;
        }

        /* ── Language dot — make it bigger ─────────────────────────── */
        .react-flow__node-codeNode .w-2.h-2 {
          width: 10px !important;
          height: 10px !important;
        }

        /* ── VISIBLE edges — thicker, brighter ────────────────────── */
        .react-flow__edge path {
          stroke-opacity: 0.7 !important;
          stroke-width: 2px !important;
          shape-rendering: geometricPrecision;
        }
        .react-flow__edge marker path {
          opacity: 0.9 !important;
        }

        /* ── Hide animated dots (they cause rendering artefacts) ──── */
        .react-flow__edge circle {
          display: none !important;
        }

        /* ── Background dots — slightly brighter ─────────────────── */
        .react-flow__background {
          opacity: 0.5 !important;
        }
      `;
      document.head.appendChild(exportCSS);

      // Let the browser repaint with solid backgrounds
      await new Promise((r) => setTimeout(r, 100));

      // ── 3. Build capture options ─────────────────────────────────────
      const rect = renderer.getBoundingClientRect();
      const filter = (n) => {
        const c = n?.classList;
        if (!c) return true;
        if (c.contains("react-flow__controls")) return false;
        if (c.contains("react-flow__minimap")) return false;
        if (c.contains("react-flow__panel")) return false;
        return true;
      };

      // Bump effective DPI: at small zoom levels, the base pixel density
      // needs to be higher to keep text readable when zoomed in on the image.
      const effectiveScale = scale * 1.5;

      const opts = {
        backgroundColor: "#0e0e0e",
        pixelRatio: effectiveScale,
        width: rect.width,
        height: rect.height,
        skipFonts: true,
        quality: 1.0,
        filter,
      };

      // ── 4. Single-pass capture ───────────────────────────────────────
      let url;
      try {
        url = format === "svg"
          ? await toSvg(renderer, opts)
          : await toPng(renderer, opts);
      } finally {
        // ── 5. Cleanup ─────────────────────────────────────────────────
        document.head.removeChild(exportCSS);
        setViewport(prev, { duration: 300 });
      }

      const a = document.createElement("a");
      a.download = `${repoName || "graph"}-${new Date().toISOString().slice(0, 10)}.${format}`;
      a.href = url;
      a.click();
    },
  }));

  return (
    <div className={`w-full h-full relative group ${className}`}>
      <ReactFlow
        nodes={nodes} edges={edges}
        onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onNodeMouseEnter={handleNodeMouseEnter}
        onNodeMouseLeave={handleNodeMouseLeave}
        nodeTypes={nodeTypes} edgeTypes={edgeTypes}
        fitView fitViewOptions={{ padding: 0.12 }}
        minZoom={0.04} maxZoom={2}
        nodesDraggable
        proOptions={{ hideAttribution: true }}
        style={{ background: "#121212" }}
      >
        <Background variant={BackgroundVariant.Dots} color="rgba(182,255,59,0.06)" gap={32} size={1} />
        <Controls style={{ bottom: 24, left: 24 }} />

        {/* ── Bottom-right stack: chat button overlapping minimap top-right ── */}
        <Panel position="bottom-right" style={{ margin: 0, padding: 0 }}>
          <div
            className="flex flex-col items-end"
            style={{ paddingBottom: 24, paddingRight: 24 }}
          >
            {/* Chat trigger button */}
            <AnimatePresence>
              {!isChatOpen && (
                <motion.button
                  key="chat-bubble"
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0, opacity: 0 }}
                  whileHover={{ scale: 1.08 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={onChatOpen}
                  title={`Chat about ${repoName}`}
                  style={{
                    marginBottom: -20,
                    zIndex: 10,
                    position: "relative",
                  }}
                  className="w-12 h-12 rounded-full bg-moss shadow-lg shadow-moss/30 flex items-center justify-center"
                >
                  <MessageCircle size={20} className="text-charcoal-300" />
                  <span className="absolute inset-0 rounded-full bg-moss/40 animate-ping pointer-events-none" />
                </motion.button>
              )}
            </AnimatePresence>

            {/* MiniMap */}
            <MiniMap
              nodeColor={minimapNodeColor}
              maskColor="rgba(18,18,18,0.7)"
              style={{
                position: "relative",
                bottom: "unset",
                right: "unset",
                margin: 0,
                width: 160,
                height: 100,
              }}
            />
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
});

const GraphCanvas = forwardRef(function GraphCanvas(
  { graphData, graphKey, onNodeClick, isAnalyzing, onChatOpen, isChatOpen, repoName },
  ref
) {
  if (!graphData) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-16 h-16 rounded-2xl bg-moss/10 border border-moss/20 mx-auto flex items-center justify-center">
            <span className="text-3xl">⬡</span>
          </div>
          <p className="text-slate-500 font-display text-sm">
            Select a repository to visualise its architecture
          </p>
        </div>
      </div>
    );
  }

  return (
    <GraphCanvasInner
      ref={ref}
      graphData={graphData}
      graphKey={graphKey}
      onNodeClick={onNodeClick}
      isAnalyzing={isAnalyzing}
      onChatOpen={onChatOpen}
      isChatOpen={isChatOpen}
      repoName={repoName}
    />
  );
});

export default GraphCanvas;