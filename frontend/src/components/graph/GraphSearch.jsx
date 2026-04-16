import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X } from "lucide-react";

export default function GraphSearch({ nodes, onHighlight, onJumpTo }) {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState("");
    const [cursor, setCursor] = useState(0);
    const inputRef = useRef(null);

    const codeNodes = (nodes || []).filter((n) => n.type === "codeNode");

    const matches = query.trim()
        ? codeNodes.filter((n) =>
            n.data?.label?.toLowerCase().includes(query.toLowerCase()) ||
            n.data?.file_path?.toLowerCase().includes(query.toLowerCase())
        )
        : [];

    useEffect(() => {
        if (!open || query.trim() === "") {
            onHighlight?.(null);
            return;
        }
        onHighlight?.(new Set(matches.map((n) => n.id)));
    }, [matches.length, query, open]);

    const close = useCallback(() => {
        setOpen(false);
        setQuery("");
        setCursor(0);
        onHighlight?.(null);
    }, [onHighlight]);

    useEffect(() => {
        const handler = (e) => {
            if (e.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) {
                e.preventDefault();
                setOpen(true);
                setTimeout(() => inputRef.current?.focus(), 50);
            }
            if (e.key === "Escape") close();
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, [close]);

    const handleKey = useCallback((e) => {
        if (e.key === "ArrowDown") {
            e.preventDefault();
            setCursor((c) => Math.min(c + 1, matches.length - 1));
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setCursor((c) => Math.max(c - 1, 0));
        } else if (e.key === "Enter" && matches[cursor]) {
            onJumpTo?.(matches[cursor].id);
        } else if (e.key === "Escape") {
            close();
        }
    }, [matches, cursor, onJumpTo, close]);

    useEffect(() => { setCursor(0); }, [query]);

    return (
        <>
            {/* ── Search trigger button ───────────────────────────────────────
                top-16 (64px) places it just below the repo header bar which
                sits at top-4 (~44px tall). left-4 aligns it with the header. */}
            <AnimatePresence>
                {!open && (
                    <motion.button
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        onClick={() => {
                            setOpen(true);
                            setTimeout(() => inputRef.current?.focus(), 50);
                        }}
                        className="absolute top-[82px] left-4 z-10 flex items-center gap-2 px-3 py-1.5 rounded-lg glass border border-white/8 text-slate-600 hover:text-slate-400 hover:border-white/15 transition-all text-xs font-display"
                    >
                        <Search size={11} />
                        Search files
                        <kbd className="ml-1 px-1 py-0.5 rounded bg-white/8 text-[9px] font-mono text-slate-700">
                            /
                        </kbd>
                    </motion.button>
                )}
            </AnimatePresence>

            {/* ── Search panel ────────────────────────────────────────────────
                Same top-16 left-4 anchor as the button. Expands downward.
                Width capped at 380px so it doesn't reach the right-side toast
                or the ComponentSidebar on normal screen widths.             */}
            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ opacity: 0, y: -8, scale: 0.97 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -8, scale: 0.97 }}
                        transition={{ type: "spring", damping: 26, stiffness: 340 }}
                        className="absolute top-16 left-4 z-20 w-[380px] glass rounded-xl border border-white/10 overflow-hidden shadow-2xl"
                    >
                        {/* Input row */}
                        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/6">
                            <Search size={14} className="text-moss flex-shrink-0" />
                            <input
                                ref={inputRef}
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onKeyDown={handleKey}
                                placeholder="Search files by name or path…"
                                className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-600 outline-none"
                            />
                            {query && (
                                <span className="text-[10px] text-slate-600 font-mono flex-shrink-0">
                                    {matches.length} match{matches.length !== 1 ? "es" : ""}
                                </span>
                            )}
                            <button
                                onClick={close}
                                className="p-1 rounded text-slate-600 hover:text-slate-400"
                            >
                                <X size={13} />
                            </button>
                        </div>

                        {/* Results list */}
                        {matches.length > 0 && (
                            <div className="max-h-56 overflow-y-auto py-1">
                                {matches.map((node, i) => (
                                    <button
                                        key={node.id}
                                        onClick={() => { onJumpTo?.(node.id); close(); }}
                                        className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${i === cursor
                                            ? "bg-moss/12 text-slate-200"
                                            : "text-slate-400 hover:bg-white/4 hover:text-slate-200"
                                            }`}
                                    >
                                        <div
                                            className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                                            style={{
                                                background: node.data?.is_circular ? "#EF4444" : "#B6FF3B",
                                            }}
                                        />
                                        <div className="min-w-0 flex-1">
                                            <p className="text-xs font-mono truncate">{node.data?.label}</p>
                                            <p className="text-[10px] text-slate-600 font-mono truncate">
                                                {node.data?.file_path}
                                            </p>
                                        </div>
                                        <span className="text-[10px] text-slate-700 flex-shrink-0 font-mono">
                                            {node.data?.language}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        )}

                        {query.trim() && matches.length === 0 && (
                            <div className="px-4 py-6 text-center text-slate-600 text-sm">
                                No files matching{" "}
                                <span className="text-slate-400 font-mono">"{query}"</span>
                            </div>
                        )}

                        {/* Keyboard hints */}
                        <div className="px-4 py-2 border-t border-white/5 flex items-center gap-4">
                            {[
                                { keys: ["↑", "↓"], label: "navigate" },
                                { keys: ["↵"], label: "jump to" },
                                { keys: ["Esc"], label: "close" },
                            ].map(({ keys, label }) => (
                                <span
                                    key={label}
                                    className="flex items-center gap-1 text-[10px] text-slate-700"
                                >
                                    {keys.map((k) => (
                                        <kbd
                                            key={k}
                                            className="px-1 py-0.5 rounded bg-white/6 font-mono text-slate-600"
                                        >
                                            {k}
                                        </kbd>
                                    ))}
                                    {label}
                                </span>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}