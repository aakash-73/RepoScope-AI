import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
    X, Download, Image, FileCode,
    Loader2, CheckCircle, AlertTriangle,
} from "lucide-react";

const PRESETS = [
    { label: "Draft", scale: 1, desc: "Screen resolution" },
    { label: "Good", scale: 2, desc: "2× · recommended" },
    { label: "High", scale: 3, desc: "3× · large display" },
    { label: "Ultra", scale: 4, desc: "4× · print / poster quality" },
];

export default function GraphExportDialog({ repoName, onExport, onClose }) {
    const [format, setFormat] = useState("png");
    const [scale, setScale] = useState(2);
    const [status, setStatus] = useState("idle");
    const [errMsg, setErrMsg] = useState("");

    // Size estimate — actual dimensions are determined by graph content,
    // not the viewport, so we show the scale multiplier instead.
    const scaleLabel = `${scale}× pixel density`;

    const handleExport = useCallback(async () => {
        setStatus("exporting");
        setErrMsg("");
        try {
            await onExport(format, scale);
            setStatus("done");
            setTimeout(() => setStatus("idle"), 2200);
        } catch (err) {
            setErrMsg(err?.message || "Export failed — try a lower quality.");
            setStatus("error");
            setTimeout(() => setStatus("idle"), 3500);
        }
    }, [onExport, format, scale]);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)" }}
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <motion.div
                initial={{ scale: 0.94, opacity: 0, y: 14 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.94, opacity: 0, y: 14 }}
                transition={{ type: "spring", damping: 24, stiffness: 320 }}
                className="w-full max-w-sm glass rounded-2xl border border-white/10 overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between px-5 pt-5 pb-4 border-b border-white/6">
                    <div>
                        <h2 className="text-sm font-display font-bold text-slate-100 tracking-tight">Export Graph</h2>
                        <p className="text-[11px] text-slate-600 mt-0.5">
                            {repoName && <span className="text-moss/80 font-mono">{repoName} · </span>}
                            captures the full canvas
                        </p>
                    </div>
                    <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors">
                        <X size={15} />
                    </button>
                </div>

                <div className="px-5 py-5 space-y-5">
                    <div>
                        <p className="text-[10px] uppercase tracking-wider text-slate-600 font-display mb-2">Format</p>
                        <div className="grid grid-cols-2 gap-2">
                            {[
                                { id: "png", Icon: Image, label: "PNG", sub: "Raster · great for sharing" },
                                { id: "svg", Icon: FileCode, label: "SVG", sub: "Vector · infinitely scalable" },
                            ].map(({ id, Icon, label, sub }) => (
                                <button key={id} onClick={() => setFormat(id)}
                                    className={`flex items-start gap-2.5 p-3 rounded-xl border transition-all text-left ${format === id
                                            ? "bg-moss/12 border-moss/35 text-slate-200"
                                            : "bg-white/3 border-white/8 text-slate-500 hover:border-white/15 hover:text-slate-400"
                                        }`}
                                >
                                    <Icon size={14} className={`mt-0.5 ${format === id ? "text-moss" : ""}`} />
                                    <div>
                                        <p className="text-xs font-display font-semibold leading-none">{label}</p>
                                        <p className="text-[10px] mt-1 leading-tight opacity-70">{sub}</p>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className={format === "svg" ? "opacity-40 pointer-events-none select-none" : ""}>
                        <div className="flex items-center justify-between mb-2">
                            <p className="text-[10px] uppercase tracking-wider text-slate-600 font-display">
                                Quality
                                {format === "svg" && <span className="normal-case text-slate-700 ml-1">(SVG is always lossless)</span>}
                            </p>
                            <span className="text-[10px] font-mono text-moss/80">Full canvas · {scaleLabel}</span>
                        </div>
                        <div className="grid grid-cols-4 gap-1.5 mb-3">
                            {PRESETS.map((p) => (
                                <button key={p.scale} onClick={() => setScale(p.scale)}
                                    className={`py-1.5 rounded-lg text-[11px] font-display font-semibold border transition-all ${scale === p.scale
                                            ? "bg-moss/20 border-moss/40 text-moss"
                                            : "bg-white/3 border-white/8 text-slate-500 hover:border-white/15"
                                        }`}
                                >
                                    {p.label}
                                </button>
                            ))}
                        </div>
                        <input
                            type="range" min={1} max={4} step={0.5} value={scale}
                            onChange={(e) => setScale(parseFloat(e.target.value))}
                            className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                            style={{
                                background: `linear-gradient(to right, #B6FF3B ${((scale - 1) / 3) * 100}%, rgba(255,255,255,0.1) ${((scale - 1) / 3) * 100}%)`,
                                accentColor: "#B6FF3B",
                            }}
                        />
                        <div className="flex justify-between mt-1">
                            <span className="text-[9px] text-slate-700">1×</span>
                            <span className="text-[9px] text-slate-600">{PRESETS.find((p) => p.scale === scale)?.desc ?? `${scale}× pixel density`}</span>
                            <span className="text-[9px] text-slate-700">4×</span>
                        </div>
                    </div>

                    <button onClick={handleExport} disabled={status === "exporting"}
                        className={`w-full flex items-center justify-center gap-2.5 py-3 rounded-xl text-sm font-display font-semibold transition-all active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed ${status === "done" ? "bg-emerald-500/20 border border-emerald-500/30 text-emerald-400"
                                : status === "error" ? "bg-red-500/15 border border-red-500/25 text-red-400"
                                    : "bg-moss/25 border border-moss/35 text-moss hover:bg-moss/35"
                            }`}
                    >
                        {status === "exporting" && <Loader2 size={15} className="animate-spin" />}
                        {status === "done" && <CheckCircle size={15} />}
                        {status === "error" && <AlertTriangle size={15} />}
                        {status === "idle" && <Download size={15} />}
                        {status === "exporting" ? "Rendering…"
                            : status === "done" ? "Downloaded!"
                                : status === "error" ? (errMsg || "Export failed")
                                    : `Download ${format.toUpperCase()}`}
                    </button>
                </div>
            </motion.div>
        </motion.div>
    );
}