import React, { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  X, ChevronRight, Loader2, Network, CheckCircle2,
  FolderGit2, BookOpen, LayoutDashboard, ScanSearch, Download, MessageSquare,
} from "lucide-react";

export const TOUR_COMPLETED_KEY = "reposcope_tour_completed";

// ── Step definitions ──────────────────────────────────────────────────────────
const STEPS = [
  {
    id: "welcome",
    selector: null,
    title: "Welcome to RepoScope AI",
    Icon: Network,
    body: "The premier AI-powered codebase architecture explorer. This quick tour walks you through every core feature — takes under 2 minutes.",
  },
  {
    id: "import",
    selector: ".tour-import-btn",
    isImportStep: true,
    title: "Import a Repository",
    Icon: FolderGit2,
    body: "Click Import Repository and paste a GitHub URL. The tour automatically continues once your repository graph is ready.",
  },
  {
    id: "repos",
    selector: ".tour-repo-list",
    title: "Repository Library",
    Icon: BookOpen,
    body: "All your imported repositories live here. Click any entry to switch the active project — the graph, search, and AI chat update instantly.",
  },
  {
    id: "controls",
    selector: ".tour-graph-controls",
    title: "Graph Controls",
    Icon: LayoutDashboard,
    body: "Toggle between Structure (file imports) and Semantic (logical grouping) views. Enable Build Mode to watch AI analysis solidify in real-time.",
  },
  {
    id: "canvas",
    selector: ".tour-graph-canvas",
    title: "Architecture Canvas",
    Icon: ScanSearch,
    body: "Scroll to zoom, drag to pan, and click any node to open an AI-generated insight panel on the right.",
  },
  {
    id: "export",
    selector: ".tour-export-btn",
    title: "Export Capabilities",
    Icon: Download,
    body: "Export your architecture as a high-resolution PNG or SVG — perfect for technical documentation and presentations.",
  },
  {
    id: "chat",
    selector: ".tour-chat-btn",
    title: "AI Code Companion",
    Icon: MessageSquare,
    body: 'Ask natural-language questions: "What does AuthService depend on?" or "Summarise the data layer." The AI knows your entire architecture.',
    note: "Full analysis must complete before the AI companion becomes available.",
  },
];

// ── Measure a DOM element's rect, update on resize ───────────────────────────
function useElementRect(selector) {
  const [rect, setRect] = useState(null);
  useEffect(() => {
    if (!selector) { setRect(null); return; }
    const measure = () => {
      const el = document.querySelector(selector);
      setRect(el ? el.getBoundingClientRect() : null);
    };
    measure();
    const id = setInterval(measure, 400);
    window.addEventListener("resize", measure);
    return () => { clearInterval(id); window.removeEventListener("resize", measure); };
  }, [selector]);
  return rect;
}

// ── Overlay: full-screen or 4-rect with spotlight ────────────────────────────
const OVERLAY_BG   = "rgba(0,0,0,0.80)"; // surrounding dark
const INNER_BG     = "rgba(0,0,0,0.28)"; // lighter inside spotlight (element still visible)
const OZ = 950; // overlay z-index

function Overlay({ step, rect }) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const pad = 8;
  const base = { position: "fixed", zIndex: OZ, pointerEvents: "all" };

  // Import step: pure hole — no inner overlay so the button is fully clickable
  if (step.isImportStep && rect) {
    const { left, top, right, bottom } = rect;
    return (
      <>
        <div style={{ ...base, background: OVERLAY_BG, left: 0, top: 0, width: vw, height: Math.max(0, top - pad) }} />
        <div style={{ ...base, background: OVERLAY_BG, left: 0, top: bottom + pad, width: vw, height: Math.max(0, vh - bottom - pad) }} />
        <div style={{ ...base, background: OVERLAY_BG, left: 0, top: top - pad, width: Math.max(0, left - pad), height: bottom - top + pad * 2 }} />
        <div style={{ ...base, background: OVERLAY_BG, left: right + pad, top: top - pad, width: Math.max(0, vw - right - pad), height: bottom - top + pad * 2 }} />
      </>
    );
  }

  // Steps with a target: 4-rect dark surround + lighter inner spotlight (blocks clicks but shows element)
  if (rect) {
    const { left, top, right, bottom } = rect;
    return (
      <>
        {/* Outer 4 dark rects */}
        <div style={{ ...base, background: OVERLAY_BG, left: 0, top: 0, width: vw, height: Math.max(0, top - pad) }} />
        <div style={{ ...base, background: OVERLAY_BG, left: 0, top: bottom + pad, width: vw, height: Math.max(0, vh - bottom - pad) }} />
        <div style={{ ...base, background: OVERLAY_BG, left: 0, top: top - pad, width: Math.max(0, left - pad), height: bottom - top + pad * 2 }} />
        <div style={{ ...base, background: OVERLAY_BG, left: right + pad, top: top - pad, width: Math.max(0, vw - right - pad), height: bottom - top + pad * 2 }} />
        {/* Lighter inner overlay — visually highlights element, still blocks accidental clicks */}
        <div style={{ ...base, background: INNER_BG, left: left - pad, top: top - pad, width: right - left + pad * 2, height: bottom - top + pad * 2 }} />
      </>
    );
  }

  // Welcome / no selector: full opaque overlay
  return <div style={{ ...base, background: OVERLAY_BG, inset: 0 }} />;
}

// ── Glow ring around highlighted element ─────────────────────────────────────
function SpotlightRing({ rect }) {
  if (!rect) return null;
  const pad = 8;
  return (
    <div
      style={{
        position: "fixed",
        left: rect.left - pad,
        top: rect.top - pad,
        width: rect.width + pad * 2,
        height: rect.height + pad * 2,
        borderRadius: 10,
        border: "2px solid rgba(182,255,59,0.55)",
        boxShadow: "0 0 0 4px rgba(182,255,59,0.08), 0 0 24px rgba(182,255,59,0.2)",
        pointerEvents: "none",
        zIndex: OZ + 2,
        transition: "all 0.3s ease",
      }}
    />
  );
}

// ── Progress dots ─────────────────────────────────────────────────────────────
function Dots({ total, current }) {
  return (
    <div className="flex items-center gap-1.5">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`rounded-full transition-all duration-300 ${
            i === current
              ? "w-5 h-2 bg-moss shadow-[0_0_8px_rgba(182,255,59,0.5)]"
              : i < current
              ? "w-2 h-2 bg-moss/35"
              : "w-2 h-2 bg-white/10"
          }`}
        />
      ))}
    </div>
  );
}

// ── Smart card position (right → below → above → left of target) ─────────────
function cardStyle(rect) {
  const W = 340, H = 260, PAD = 16;
  const vw = window.innerWidth, vh = window.innerHeight;
  const z = { position: "fixed", zIndex: OZ + 3, width: W };

  if (!rect) return { ...z, left: "50%", top: "50%", transform: "translate(-50%,-50%)" };

  if (rect.right + W + PAD < vw)
    return { ...z, left: rect.right + PAD, top: Math.max(PAD, Math.min(rect.top, vh - H - PAD)) };
  if (rect.bottom + H + PAD < vh)
    return { ...z, left: Math.max(PAD, Math.min(rect.left, vw - W - PAD)), top: rect.bottom + PAD };
  if (rect.top - H - PAD > 0)
    return { ...z, left: Math.max(PAD, Math.min(rect.left, vw - W - PAD)), top: rect.top - H - PAD };
  return { ...z, left: Math.max(PAD, rect.left - W - PAD), top: Math.max(PAD, Math.min(rect.top, vh - H - PAD)) };
}

// ── Tour card UI ──────────────────────────────────────────────────────────────
function TourCard({ step, stepIndex, totalSteps, rect, isGraphReady, isGraphLoading, onNext, onBack, onClose }) {
  const { Icon, title, body, note, isImportStep } = step;
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === totalSteps - 1;

  let importState = null;
  if (isImportStep) {
    if (isGraphLoading)     importState = "loading";
    else if (!isGraphReady) importState = "waiting";
    else                    importState = "success";
  }
  const disabled = importState === "loading" || importState === "waiting";
  const nextLabel = importState === "loading" ? "Loading…"
    : importState === "waiting" ? "Waiting for Import…"
    : isLast ? "Finish" : "Next";

  const style = isFirst
    ? { position: "fixed", zIndex: OZ + 3, left: "50%", top: "50%", transform: "translate(-50%,-50%)", width: 420 }
    : cardStyle(rect);

  return (
    <div style={style} className="glass font-display p-6 relative">
      {/* Close */}
      <button
        onClick={onClose}
        className="absolute top-3.5 right-3.5 w-7 h-7 rounded-lg bg-charcoal-50 border border-white/8 text-slate-500 hover:text-slate-200 flex items-center justify-center transition-colors"
      >
        <X size={13} />
      </button>

      {/* Welcome extra: steps preview grid */}
      {isFirst ? (
        <>
          <div className="w-14 h-14 rounded-2xl bg-moss/10 border border-moss/20 flex items-center justify-center mb-4">
            <Icon size={26} className="text-moss" />
          </div>
          <h2 className="text-xl font-bold text-slate-100 mb-2">{title}</h2>
          <p className="text-slate-400 text-sm leading-relaxed mb-5">{body}</p>
          <div className="grid grid-cols-2 gap-2 mb-6">
            {STEPS.slice(1).map(({ Icon: SI, title: st }, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-2 bg-charcoal-50/40 border border-white/5 rounded-lg">
                <SI size={12} className="text-slate-500 flex-shrink-0" />
                <span className="text-xs text-slate-500 truncate">{st}</span>
              </div>
            ))}
          </div>
          <div className="flex gap-3">
            <button onClick={onNext} className="btn-moss flex-1 flex items-center justify-center gap-2">
              Start Tour <ChevronRight size={15} />
            </button>
            <button onClick={onClose} className="btn-ghost px-5 text-sm">Skip</button>
          </div>
        </>
      ) : (
        <>
          {/* Header */}
          <div className="flex items-center gap-3 mb-3 pr-8">
            <div className="w-8 h-8 rounded-lg bg-moss/10 border border-moss/20 flex items-center justify-center flex-shrink-0">
              <Icon size={15} className="text-moss" />
            </div>
            <h3 className="text-sm font-bold text-slate-100">{title}</h3>
          </div>

          {/* Body */}
          <p className="text-slate-400 text-sm leading-relaxed mb-3">{body}</p>

          {/* Note */}
          {note && (
            <div className="mb-3 px-3 py-2 bg-moss/8 border border-moss/20 rounded-lg text-xs text-moss/80">{note}</div>
          )}

          {/* Import status */}
          {isImportStep && (
            <div className={`mb-4 px-3 py-2.5 rounded-lg border text-xs flex items-center gap-2 transition-all ${
              importState === "success" ? "bg-moss/8 border-moss/25 text-moss"
              : importState === "loading" ? "bg-moss/5 border-moss/15 text-moss/70"
              : "bg-charcoal-50/60 border-white/5 text-slate-500"
            }`}>
              {importState === "loading" && <><Loader2 size={13} className="animate-spin flex-shrink-0" /> Downloading &amp; analysing graph…</>}
              {importState === "waiting" && <><div className="w-3 h-3 rounded-full border border-slate-600 flex-shrink-0" /> Import a repository above to continue.</>}
              {importState === "success" && <><CheckCircle2 size={13} className="flex-shrink-0" /> Repository ready — advancing automatically…</>}
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between pt-3.5 border-t border-white/5">
            <Dots total={totalSteps} current={stepIndex} />
            <div className="flex gap-2">
              {stepIndex > 1 && !isImportStep && (
                <button onClick={onBack} className="btn-ghost px-3 py-1.5 text-xs">Back</button>
              )}
              <button
                onClick={onNext}
                disabled={disabled}
                className={`btn-moss px-4 py-1.5 text-xs flex items-center gap-1.5 ${disabled ? "opacity-40 cursor-not-allowed hover:bg-moss active:scale-100" : ""}`}
              >
                {importState === "loading" && <Loader2 size={12} className="animate-spin" />}
                {nextLabel}
                {!disabled && !isLast && <ChevronRight size={13} />}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Portal: overlay + ring + card ────────────────────────────────────────────
function TourPortal({ isOpen, stepIndex, isGraphReady, isGraphLoading, onNext, onBack, onClose }) {
  const step = STEPS[stepIndex];
  const rect = useElementRect(step?.selector ?? null);

  if (!isOpen) return null;

  return createPortal(
    <>
      <Overlay step={step} rect={rect} />
      {rect && stepIndex !== 1 && <SpotlightRing rect={rect} />}
      <TourCard
        step={step}
        stepIndex={stepIndex}
        totalSteps={STEPS.length}
        rect={rect}
        isGraphReady={isGraphReady}
        isGraphLoading={isGraphLoading}
        onNext={onNext}
        onBack={onBack}
        onClose={onClose}
      />
    </>,
    document.body
  );
}

// ── Main wrapper ──────────────────────────────────────────────────────────────
export default function GuidedTourWrapper({ children, run, onFinish, isGraphReady, isGraphLoading }) {
  const [isOpen, setIsOpen]       = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const autoAdvancedRef           = useRef(false);

  // Start tour when run=true
  useEffect(() => {
    if (run && !isOpen) {
      setStepIndex(0);
      setIsOpen(true);
      autoAdvancedRef.current = false;
    }
  }, [run]); // eslint-disable-line react-hooks/exhaustive-deps

  // Notify parent on close
  useEffect(() => {
    if (!isOpen && run) onFinish?.();
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-advance import step → repo list when graph is ready
  useEffect(() => {
    if (isGraphReady && stepIndex === 1 && isOpen && !autoAdvancedRef.current) {
      autoAdvancedRef.current = true;
      setTimeout(() => setStepIndex(2), 1500);
    }
  }, [isGraphReady, stepIndex, isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleClose = useCallback(() => { setIsOpen(false); onFinish?.(); }, [onFinish]);

  const handleNext = useCallback(() => {
    if (stepIndex === STEPS.length - 1) {
      localStorage.setItem(TOUR_COMPLETED_KEY, "true");
      handleClose();
    } else {
      setStepIndex((s) => s + 1);
    }
  }, [stepIndex, handleClose]);

  const handleBack = useCallback(() => {
    setStepIndex((s) => Math.max(0, s - 1));
  }, []);

  return (
    <>
      {children}
      <TourPortal
        isOpen={isOpen}
        stepIndex={stepIndex}
        isGraphReady={isGraphReady}
        isGraphLoading={isGraphLoading}
        onNext={handleNext}
        onBack={handleBack}
        onClose={handleClose}
      />
    </>
  );
}
