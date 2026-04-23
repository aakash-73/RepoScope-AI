import React, { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { AlertTriangle, Ghost, Layers, Shield, FlaskConical } from "lucide-react";
import { getLanguageColor } from "../../lib/utils";
import { motion } from "framer-motion";

function complexityHeat(score) {
  if (!score || score <= 2) return null;
  if (score <= 4) return "rgba(234,179,8,0.08)";
  if (score <= 6) return "rgba(249,115,22,0.10)";
  if (score <= 8) return "rgba(239,68,68,0.12)";
  return "rgba(239,68,68,0.20)";
}

function complexityBorderColor(score) {
  if (!score || score <= 2) return null;
  if (score <= 4) return "rgba(234,179,8,0.25)";
  if (score <= 6) return "rgba(249,115,22,0.30)";
  if (score <= 8) return "rgba(239,68,68,0.35)";
  return "rgba(239,68,68,0.55)";
}

function complexityLabel(score) {
  if (!score || score <= 3) return null;
  if (score <= 5) return { text: "moderate", color: "text-yellow-500/70" };
  if (score <= 7) return { text: "complex", color: "text-orange-400/80" };
  if (score <= 9) return { text: "hot", color: "text-red-400/90" };
  return { text: "critical", color: "text-red-400 font-bold" };
}

function nodeWidth(lines) {
  const l = lines || 0;
  const t = Math.min(l / 500, 1);
  return Math.round(200 + t * 140);
}

const HANDLE_STYLE = {
  width: 6,
  height: 6,
  border: "none",
  borderRadius: "50%",
  opacity: 0,
};

function CodeNode({ data, selected }) {
  const isHub = data.kind && data.kind !== "file";
  const langColor = data.node_color || getLanguageColor(data.language);

  if (isHub || data.isSemantic) {
    const isSatellite = data.isSemantic && !isHub;
    
    // Dynamic sizing based on text length to establish hierarchy and ensure text fits
    const charLen = data.label ? data.label.length : 10;
    const baseSize = isHub ? Math.max(130, charLen * 8.5 + 40) : Math.max(85, charLen * 7 + 30);
    // Cap sizes to prevent completely massive circles
    const size = Math.min(250, baseSize);
    
    const color = isHub ? (data.node_color || "#3B82F6") : langColor;
    
    return (
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className={`
          relative rounded-full flex flex-col items-center justify-center text-center
          border-2 cursor-pointer z-10
          ${selected ? "ring-2 ring-white/20" : ""}
        `}
        style={{
          width: size,
          height: size,
          background: "#000000",
          borderColor: color,
          boxShadow: isSatellite 
            ? `0 0 25px ${color}90, inset 0 0 15px ${color}50` 
            : `0 0 15px ${color}40`,
        }}
      >
        <div className="flex flex-col items-center justify-center pt-3 pb-2 px-2 w-full h-full text-white">
            <span className="text-[10px] text-slate-400 font-mono tracking-wide opacity-80 overflow-hidden text-ellipsis whitespace-nowrap max-w-full">
                {isSatellite ? (data.language || "file") : data.kind}
            </span>
            <p className="text-[13px] font-display font-bold leading-tight break-words max-w-full mt-1 mb-auto flex-1 flex items-center justify-center text-white">
                {data.label}
            </p>
            <div className="mt-1 opacity-50 flex items-center justify-center w-full">
                <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
                    <path d="M5 6L0 0H10L5 6Z" fill="#9CA3AF"/>
                </svg>
            </div>
        </div>
        
        <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
        <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
      </motion.div>
    );
  }

  const isCircular = data.is_circular;
  const isDeadCode = data.is_dead_code || data.is_dead;
  const isTestFile = data.is_test_file || false;
  const isTested = data.is_tested || false;
  const githubUrl = data.github_url;
  const score = data.complexity_score ?? 1;
  const depthVal = data.dependency_depth;
  const width = nodeWidth(data.lines);

  const applyHeat = !isCircular && !selected;
  const heatBg = applyHeat ? complexityHeat(score) : null;
  const heatBorder = applyHeat ? complexityBorderColor(score) : null;
  const heatLabel = complexityLabel(score);

  // FIX 4: Only treat explicitly "pending" nodes as ghosted.
  // Previously, missing analysis_status also triggered ghosting (due to `!data.analysis_status`),
  // which was correct. But "failed" nodes were also ghosted because they never matched "done".
  // Now "failed" is treated as solidified — the node renders fully so the user can see it and
  // interact with it (e.g. double-click to re-analyze), even without AI data attached.
  const isPending = data.analysis_status === "pending";
  const isAnalyzing = data.analysis_status === "analyzing";
  const isFailed = data.analysis_status === "failed";

  return (
    <motion.div
      animate={{
        scale: 1,
        opacity: isPending ? 0.45 : 1,
        filter: isPending ? "grayscale(80%) brightness(0.8)" : "grayscale(0%) brightness(1)",
      }}
      transition={{ 
        type: "spring", 
        stiffness: 500, 
        damping: 30,
        filter: { type: "tween", duration: 0.3 }
      }}
      className={`
        relative rounded-xl border transition-all duration-300 cursor-pointer
        ${selected
          ? "border-moss shadow-moss bg-charcoal-100"
          : isAnalyzing
            ? "border-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.4)] bg-charcoal-100 animate-pulse"
            : isCircular
              ? "border-red-500/80 bg-charcoal-100"
              : isFailed
                ? "border-orange-500/40 bg-charcoal-100/90"
                : isPending
                  ? "border-white/5 bg-transparent"
                  : "border-white/10 bg-charcoal-100/90 hover:border-moss/40 hover:shadow-moss-sm"
        }
      `}
      style={{
        width: `${width}px`,
        background: isPending ? "transparent" : (heatBg || "#1e1e1e"),
        borderColor: heatBorder || undefined,
        boxShadow: isCircular
          ? "0 0 0 1px rgba(239,68,68,0.4), 0 0 16px rgba(239,68,68,0.3), 0 0 32px rgba(239,68,68,0.15)"
          : (score >= 8 && !isPending)
            ? "0 0 12px rgba(239,68,68,0.12)"
            : (score >= 6 && !isPending)
              ? "0 0 10px rgba(249,115,22,0.10)"
              : isPending ? "none" : "0 6px 24px rgba(0,0,0,0.25)",
      }}
    >
      <div
        className="absolute top-0 left-0 right-0 h-0.5 rounded-t-xl"
        style={{
          background: isCircular ? "#EF4444" : langColor,
          opacity: isPending ? 0.3 : 1,
        }}
      />

      {isDeadCode && !isCircular && !isTestFile && !isPending && (
        <div className="absolute -top-3 left-2 flex items-center gap-1 bg-slate-700 text-slate-300 text-[9px] font-bold px-1.5 py-0.5 rounded-full">
          <Ghost size={8} />
          dead code
        </div>
      )}

      {isTestFile && !isPending && (
        <div className="absolute -top-3 left-2 flex items-center gap-1 bg-blue-600/80 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full">
          <FlaskConical size={8} />
          test
        </div>
      )}

      {isTested && !isTestFile && !isCircular && !isPending && (
        <div className="absolute -top-3 left-2 flex items-center gap-1 bg-emerald-600/80 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full">
          <Shield size={8} />
          tested
        </div>
      )}

      {isCircular && !isPending && (
        <div className="absolute -top-3 right-2 flex items-center gap-1 bg-red-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full shadow-lg">
          <AlertTriangle size={8} />
          circular
        </div>
      )}

      {isAnalyzing && (
        <div className="absolute -top-3 right-2 flex items-center gap-1 bg-cyan-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full shadow-[0_0_10px_rgba(34,211,238,0.5)]">
          <Layers size={8} className="animate-spin" />
          thinking…
        </div>
      )}

      {/* Show a subtle badge for failed nodes so the user knows they can double-click to retry */}
      {isFailed && !isAnalyzing && (
        <div className="absolute -top-3 right-2 flex items-center gap-1 bg-orange-500/80 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full">
          <AlertTriangle size={8} />
          retry
        </div>
      )}

      <div className="px-3 py-3 pt-3.5">
        <div className="flex items-start gap-2 mb-2">
          <div
            className="w-2 h-2 rounded-full mt-1 flex-shrink-0"
            style={{ background: isCircular ? "#EF4444" : langColor }}
          />
          <p
            className="text-sm font-mono text-slate-300 leading-tight break-all"
            title={data.file_path}
          >
            {data.label}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="badge badge-gray text-[11px]">
            {data.language}
          </span>

          <span className="text-[11px] text-slate-600 font-mono">
            {data.lines}L
          </span>

          {depthVal >= 0 && (
            <span className="flex items-center gap-0.5 text-[10px] text-cyan-500/70 font-mono" title="Dependency depth from entry">
              <Layers size={9} />
              {depthVal}
            </span>
          )}

          {data.exports?.length > 0 && (
            <span className="text-[10px] text-moss/70 font-mono">
              ↑{data.exports.length}
            </span>
          )}

          {heatLabel && (
            <span className={`text-[9px] font-display font-semibold ml-auto ${heatLabel.color}`}>
              {heatLabel.text}
            </span>
          )}

          {githubUrl && (
            <a
              href={githubUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="ml-auto text-slate-700 hover:text-moss transition-colors"
              title="Open on GitHub"
            >
              <svg width="11" height="11" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
              </svg>
            </a>
          )}
        </div>
      </div>

      <Handle type="target" position={Position.Top} id="t" style={HANDLE_STYLE} />
      <Handle type="target" position={Position.Bottom} id="b-in" style={HANDLE_STYLE} />
      <Handle type="target" position={Position.Left} id="l" style={HANDLE_STYLE} />
      <Handle type="target" position={Position.Right} id="r-in" style={HANDLE_STYLE} />

      <Handle
        type="source"
        position={Position.Bottom}
        id="b"
        style={{
          ...HANDLE_STYLE,
          background: isCircular
            ? "rgba(239,68,68,0.6)"
            : "rgba(182,255,59,0.6)",
        }}
      />
      <Handle type="source" position={Position.Top} id="t-out" style={HANDLE_STYLE} />
      <Handle type="source" position={Position.Left} id="l-out" style={HANDLE_STYLE} />
      <Handle type="source" position={Position.Right} id="r" style={HANDLE_STYLE} />
    </motion.div>
  );
}

export default memo(CodeNode);