import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Github, Loader2, CheckCircle } from "lucide-react";
import { importRepo } from "../../lib/api";

export default function ImportDialog({ onClose, onSuccess }) {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(null);

  async function handleImport(e) {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await importRepo(url.trim(), branch.trim() || "main");
      setDone(result);
      setTimeout(() => {
        onSuccess?.(result);
        onClose?.();
      }, 1500);
    } catch (err) {
      setError(err.response?.data?.detail || "The Repository you are trying to import already exists");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}
        onClick={(e) => e.target === e.currentTarget && onClose?.()}
      >
        <motion.div
          initial={{ scale: 0.92, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.92, opacity: 0, y: 20 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="glass w-full max-w-md p-6"
        >
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-moss/15 border border-moss/20 flex items-center justify-center">
                <Github size={16} className="text-moss" />
              </div>
              <div>
                <h2 className="font-display font-semibold text-slate-200">
                  Import Repository
                </h2>
                <p className="text-xs text-slate-500">
                  Ingest a GitHub repo for analysis
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          {done ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center py-6 space-y-3"
            >
              <CheckCircle className="text-moss mx-auto" size={40} />
              <p className="font-display font-semibold text-slate-200">
                {done.name} imported!
              </p>
              <p className="text-sm text-slate-500">
                {done.file_count} files ingested
              </p>
            </motion.div>
          ) : (
            <form onSubmit={handleImport} className="space-y-4">
              <div>
                <label className="block text-xs text-slate-500 font-display mb-1.5">
                  GitHub URL or owner/repo
                </label>
                <input
                  className="input-field"
                  placeholder="https://github.com/facebook/react  or  facebook/react"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-slate-500 font-display mb-1.5">
                  Branch
                </label>
                <input
                  className="input-field"
                  placeholder="main"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  disabled={loading}
                />
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="btn-ghost flex-1"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-moss flex-1 flex items-center justify-center gap-2"
                  disabled={loading || !url.trim()}
                >
                  {loading ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Importing…
                    </>
                  ) : (
                    "Import"
                  )}
                </button>
              </div>
            </form>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
