import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, FilePlus, FileX, FilePen, RefreshCw } from "lucide-react";

/**
 * Shows a diff summary panel after a repo sync.
 * Props:
 *   diff   — { added: [], removed: [], modified: [] }
 *   onDismiss — callback to close
 */
export default function SyncDiffPanel({ diff, onDismiss }) {
  if (!diff) return null;

  const { added = [], removed = [], modified = [] } = diff;
  const total = added.length + removed.removed + modified.length;

  if (total === 0 && added.length === 0 && removed.length === 0 && modified.length === 0) {
    return null;
  }

  const Section = ({ icon: Icon, label, files, color }) => {
    if (!files?.length) return null;
    return (
      <div>
        <div className={`flex items-center gap-1.5 text-xs font-semibold mb-1 ${color}`}>
          <Icon size={11} />
          <span>{label} ({files.length})</span>
        </div>
        <ul className="space-y-0.5 max-h-24 overflow-y-auto">
          {files.map((f) => (
            <li key={f} className="text-[11px] text-slate-500 font-mono truncate pl-2">
              {f}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -12, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.97 }}
        className="absolute top-16 left-1/2 -translate-x-1/2 z-40 w-80 glass rounded-2xl shadow-2xl overflow-hidden"
      >
        <div className="px-4 py-3 border-b border-white/5 flex items-center gap-2">
          <RefreshCw size={13} className="text-moss" />
          <p className="text-sm font-display font-semibold text-slate-200 flex-1">Sync Complete</p>
          <button
            onClick={onDismiss}
            className="p-1 rounded-lg hover:bg-white/5 text-slate-600 hover:text-slate-400 transition-colors"
          >
            <X size={13} />
          </button>
        </div>
        <div className="px-4 py-3 space-y-3">
          <Section icon={FilePlus}  label="Added"    files={added}    color="text-emerald-400" />
          <Section icon={FilePen}   label="Modified" files={modified}  color="text-amber-400" />
          <Section icon={FileX}     label="Removed"  files={removed}   color="text-red-400" />
          {added.length === 0 && modified.length === 0 && removed.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-2">No file changes detected</p>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
