import React, { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Layers, RotateCcw, Check, X, Loader2 } from "lucide-react";
import { fetchLanguages, updateLanguageColor } from "../../lib/api";

export default function LanguageLegend({ repoId, isRepoOpen, onColorChange }) {
    const [open, setOpen] = useState(false);
    const [languages, setLanguages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [editing, setEditing] = useState(null);
    const [editColor, setEditColor] = useState("");
    const [saving, setSaving] = useState(false);
    const [savedKey, setSavedKey] = useState(null);
    const colorInputRef = useRef(null);

    const load = useCallback(async () => {
        if (!repoId) return;
        setLoading(true);
        try {
            const data = await fetchLanguages(repoId);
            setLanguages(data || []);
        } catch {
        } finally {
            setLoading(false);
        }
    }, [repoId]);

    useEffect(() => {
        if (repoId && isRepoOpen) {
            load();
        } else {
            setLanguages([]);
            setOpen(false);
        }
    }, [repoId, isRepoOpen]);

    // Hide entirely when no repo is open
    if (!isRepoOpen || !repoId) return null;
    if (languages.length === 0 && !loading) return null;

    const grouped = languages.reduce((acc, lang) => {
        if (!acc[lang.category]) acc[lang.category] = [];
        acc[lang.category].push(lang);
        return acc;
    }, {});

    const categoryOrder = [
        "frontend", "backend", "html", "css", "database",
        "mobile", "devops", "test", "config", "docs",
        "shader", "data", "other",
    ];
    const sortedCategories = [
        ...categoryOrder.filter((c) => grouped[c]),
        ...Object.keys(grouped).filter((c) => !categoryOrder.includes(c)),
    ];

    const startEdit = (lang) => {
        setEditing(lang.key);
        setEditColor(lang.color);
        setTimeout(() => colorInputRef.current?.click(), 50);
    };

    const cancelEdit = () => {
        setEditing(null);
        setEditColor("");
    };

    const saveColor = async (key, color) => {
        setSaving(true);
        try {
            const updated = await updateLanguageColor(key, color, repoId);
            setLanguages((prev) =>
                prev.map((l) =>
                    l.key === key
                        ? { ...l, color: updated.color, custom_color: updated.custom_color }
                        : l
                )
            );
            if (onColorChange) onColorChange(key, updated.color);
            setSavedKey(key);
            setTimeout(() => setSavedKey(null), 1800);
        } catch {
        } finally {
            setSaving(false);
            setEditing(null);
        }
    };

    const resetColor = async (key) => {
        setSaving(true);
        try {
            const updated = await updateLanguageColor(key, null, repoId);
            setLanguages((prev) =>
                prev.map((l) =>
                    l.key === key
                        ? { ...l, color: updated.color, custom_color: null }
                        : l
                )
            );
            if (onColorChange) onColorChange(key, updated.color);
        } catch {
        } finally {
            setSaving(false);
        }
    };

    return (
        <div
            className="absolute bottom-[170px] left-8 z-20"
            style={{ pointerEvents: "all" }}
        >
            <button
                onClick={() => setOpen((v) => !v)}
                className="flex items-center justify-center aspect-square w-10 rounded-lg glass border border-white/10 text-xs font-display text-slate-400 hover:text-slate-200 hover:border-white/20 transition-all"
                title="Detected Languages"
            >
                <Layers size={12} />
            </button>

            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ opacity: 0, y: 8, scale: 0.97 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 8, scale: 0.97 }}
                        transition={{ type: "spring", damping: 24, stiffness: 300 }}
                        className="absolute bottom-full mb-2 left-0 w-72 max-h-[420px] overflow-y-auto glass rounded-xl border border-white/10 shadow-2xl"
                    >
                        <div className="flex items-center justify-between px-4 py-3 border-b border-white/6">
                            <div className="flex items-center gap-2">
                                <Layers size={13} className="text-moss" />
                                <span className="text-xs font-display font-semibold text-slate-200">
                                    Detected Languages
                                </span>
                            </div>
                            <div className="flex items-center gap-1">
                                {loading && (
                                    <Loader2 size={12} className="animate-spin text-slate-600" />
                                )}
                                <button
                                    onClick={load}
                                    className="p-1 rounded hover:bg-white/5 text-slate-600 hover:text-slate-400 transition-colors"
                                    title="Refresh"
                                >
                                    <RotateCcw size={11} />
                                </button>
                            </div>
                        </div>

                        <div className="p-3 space-y-3">
                            {sortedCategories.map((category) => (
                                <div key={category}>
                                    <p className="text-[9px] uppercase tracking-widest text-slate-600 font-display mb-1.5 px-1">
                                        {category}
                                    </p>
                                    <div className="space-y-0.5">
                                        {grouped[category].map((lang) => (
                                            <div
                                                key={lang.key}
                                                className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-white/3 group transition-colors"
                                            >
                                                <div className="relative flex-shrink-0">
                                                    {editing === lang.key ? (
                                                        <div className="flex items-center gap-1">
                                                            <input
                                                                ref={colorInputRef}
                                                                type="color"
                                                                value={editColor}
                                                                onChange={(e) =>
                                                                    setEditColor(e.target.value)
                                                                }
                                                                className="w-5 h-5 rounded cursor-pointer border-0 bg-transparent p-0"
                                                                style={{ appearance: "none" }}
                                                            />
                                                            <button
                                                                onClick={() =>
                                                                    saveColor(lang.key, editColor)
                                                                }
                                                                disabled={saving}
                                                                className="p-0.5 rounded bg-moss/20 text-moss hover:bg-moss/30"
                                                            >
                                                                {saving ? (
                                                                    <Loader2
                                                                        size={9}
                                                                        className="animate-spin"
                                                                    />
                                                                ) : (
                                                                    <Check size={9} />
                                                                )}
                                                            </button>
                                                            <button
                                                                onClick={cancelEdit}
                                                                className="p-0.5 rounded bg-white/5 text-slate-500 hover:text-slate-300"
                                                            >
                                                                <X size={9} />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <button
                                                            onClick={() => startEdit(lang)}
                                                            className="w-4 h-4 rounded-sm border border-white/10 hover:border-white/30 hover:scale-110 transition-all flex-shrink-0 relative"
                                                            style={{ background: lang.color }}
                                                            title="Click to change color"
                                                        >
                                                            {savedKey === lang.key && (
                                                                <Check
                                                                    size={8}
                                                                    className="absolute inset-0 m-auto text-black"
                                                                />
                                                            )}
                                                        </button>
                                                    )}
                                                </div>

                                                <span className="text-[11px] text-slate-400 font-display flex-1 truncate">
                                                    {lang.display_name}
                                                </span>

                                                <span className="text-[10px] text-slate-700 font-mono flex-shrink-0">
                                                    {lang.file_count}
                                                </span>

                                                {lang.custom_color && editing !== lang.key && (
                                                    <button
                                                        onClick={() => resetColor(lang.key)}
                                                        className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded text-slate-600 hover:text-slate-400"
                                                        title="Reset to auto color"
                                                    >
                                                        <RotateCcw size={9} />
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="px-4 py-2.5 border-t border-white/5">
                            <p className="text-[9px] text-slate-700 text-center">
                                Click a color swatch to customize · changes apply to this repo
                            </p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}