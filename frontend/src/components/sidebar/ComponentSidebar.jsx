import React, { useState, useEffect, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, Loader2, Cpu, GitBranch, FileCode, AlertTriangle,
  Copy, Zap, ExternalLink, GitMerge, ArrowUpRight, Ghost, Flame, TrendingUp, Layers,
  Shield, FlaskConical
} from "lucide-react";
import { explainComponent, chatComponent, fetchNodeAnalysis } from "../../lib/api";
import { getLanguageColor } from "../../lib/utils";

function CodeBlock({ children }) {
  const [copied, setCopied] = useState(false);
  const codeString = Array.isArray(children) ? children.join("") : children;
  return (
    <div className="bg-black/20 rounded overflow-auto max-h-80 max-w-full">
      <div className="flex justify-end p-1 border-b border-white/10">
        <button onClick={() => { navigator.clipboard.writeText(codeString); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
          className="px-2 py-1 text-xs rounded bg-white/10 hover:bg-white/20 flex items-center gap-1">
          <Copy size={12} />{copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="p-2 text-xs whitespace-pre overflow-auto"><code>{codeString}</code></pre>
    </div>
  );
}

export default function ComponentSidebar({ node, repoId, graphData, refreshKey, onClose, onJumpTo }) {
  const [tab, setTab] = useState("analysis");
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chat, setChat] = useState([]);
  const [message, setMessage] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    if (!node || !repoId) return;
    setExplanation(null); setError(null); setChat([]); setMessage(""); setTab("analysis");
    fetchExplanation();
  }, [node?.id, repoId, refreshKey]);

  async function fetchExplanation() {
    const isDone = node.data.analysis_status === "done";
    if (!isDone) {
      setLoading(true);
    }
    setAnalysis(null);
    try {
      // Try fetching pre-analyzed node data
      const preAnalyzed = await fetchNodeAnalysis(repoId, node.data.file_path);
      if (preAnalyzed) {
        setAnalysis(preAnalyzed);
        // If we have the deep analysis, we can often show meaningful content even before explainComponent resolves
      }

      const res = await explainComponent(repoId, node.data.file_path);
      setExplanation(res);
    }
    catch (err) { setError(err.response?.data?.detail || "Failed to generate explanation."); }
    finally { setLoading(false); }
  }

  async function sendMessage() {
    if (!message.trim()) return;
    const userMsg = { role: "user", content: message };
    setChat((p) => [...p, userMsg]); setMessage(""); setChatLoading(true);
    try {
      const res = await chatComponent(repoId, node.data.file_path, message, chat);
      setChat((p) => [...p, { role: "assistant", content: res.reply }]);
    } catch { setChat((p) => [...p, { role: "assistant", content: "Chat failed." }]); }
    finally { setChatLoading(false); }
  }

  const impact = useMemo(() => {
    if (!graphData || !node) return { dependents: [], dependencies: [], transitiveCount: 0, transitiveDepCount: 0 };
    const allEdges = graphData.edges || [];
    const nodeById = Object.fromEntries((graphData.nodes || []).map((n) => [n.id, n]));

    const dependents = allEdges.filter((e) => e.target === node.id).map((e) => nodeById[e.source]).filter(Boolean);
    const dependencies = allEdges.filter((e) => e.source === node.id).map((e) => nodeById[e.target]).filter(Boolean);

    const importedBy = {};
    allEdges.forEach((e) => {
      if (!importedBy[e.target]) importedBy[e.target] = [];
      importedBy[e.target].push(e.source);
    });
    const imports = {};
    allEdges.forEach((e) => {
      if (!imports[e.source]) imports[e.source] = [];
      imports[e.source].push(e.target);
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

    const transitiveUpstream = traverse(node.id, importedBy);
    const transitiveDownstream = traverse(node.id, imports);

    return {
      dependents,
      dependencies,
      transitiveCount: transitiveUpstream.size,
      transitiveDepCount: transitiveDownstream.size,
    };
  }, [graphData, node?.id]);

  const langColor = getLanguageColor(node?.data?.language);
  const githubUrl = node?.data?.github_url;
  const isDeadCode = node?.data?.is_dead_code || node?.data?.is_dead;
  const isTestFile = node?.data?.is_test_file || false;
  const isTested = node?.data?.is_tested || false;
  if (!node) return null;

  return (
    <AnimatePresence>
      <motion.div
        key={node.id}
        initial={{ x: "100%", opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: "100%", opacity: 0 }}
        transition={{ type: "spring", damping: 28, stiffness: 300 }}
        className="w-[420px] flex-shrink-0 flex flex-col glass border-l border-white/5 rounded-none rounded-l-2xl overflow-hidden"
      >
        <div className="p-5 border-b border-white/5 flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: langColor }} />
              <span className="badge badge-gray">{node.data.language}</span>
              {node.data.is_circular && <span className="badge badge-danger flex items-center gap-1"><AlertTriangle size={10} />circular</span>}
              {isDeadCode && !isTestFile && <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-full bg-slate-700/60 text-slate-400"><Ghost size={9} />dead code</span>}
              {isTestFile && <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-full bg-blue-600/60 text-blue-200"><FlaskConical size={9} />test file</span>}
              {isTested && !isTestFile && <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-600/60 text-emerald-200"><Shield size={9} />tested</span>}
              {githubUrl && (
                <a href={githubUrl} target="_blank" rel="noopener noreferrer"
                  className="ml-auto flex items-center gap-1 text-[10px] text-slate-600 hover:text-moss transition-colors" title="Open on GitHub">
                  <ExternalLink size={11} />GitHub
                </a>
              )}
            </div>
            <h2 className="font-mono text-sm text-slate-200 truncate">{node.data.label}</h2>
            <p className="text-xs text-slate-600 font-mono mt-0.5 truncate">{node.data.file_path}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors flex-shrink-0"><X size={16} /></button>
        </div>

        <div className="grid grid-cols-4 gap-px bg-white/5 border-b border-white/5">
          {[
            { icon: FileCode, label: "Lines", value: node.data.lines },
            { icon: GitBranch, label: "Imports", value: node.data.imports?.length ?? 0 },
            { icon: TrendingUp, label: "Depend", value: impact.dependents.length },
            { icon: Layers, label: "Depth", value: node.data.dependency_depth >= 0 ? node.data.dependency_depth : "-" },
          ].map(({ icon: Icon, label, value }) => (
            <div key={label} className="bg-charcoal-100/60 px-2 py-3 text-center">
              <div className="flex items-center justify-center gap-1 text-slate-500 mb-1">
                <Icon size={11} /><span className="text-[10px] uppercase tracking-wider font-display">{label}</span>
              </div>
              <p className="text-lg font-display font-semibold text-moss">{value}</p>
            </div>
          ))}
        </div>

        {(() => {
          const score = node.data?.complexity_score ?? 1;
          const pct = ((score - 1) / 9) * 100;
          const color = score >= 8 ? "#EF4444" : score >= 6 ? "#F97316" : score >= 4 ? "#EAB308" : "#6B7280";
          const label = score >= 8 ? "High complexity" : score >= 6 ? "Moderate-high" : score >= 4 ? "Moderate" : "Low complexity";
          return (
            <div className="px-5 py-2.5 border-b border-white/5 flex items-center gap-3">
              <Flame size={12} style={{ color }} className="flex-shrink-0" />
              <div className="flex-1">
                <div className="flex justify-between mb-1">
                  <span className="text-[10px] text-slate-600 font-display uppercase tracking-wider">Complexity</span>
                  <span className="text-[10px] font-mono font-semibold" style={{ color }}>{score}/10 · {label}</span>
                </div>
                <div className="h-1 rounded-full bg-white/8 overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color, opacity: 0.7 }} />
                </div>
              </div>
            </div>
          );
        })()}

        <div className="flex border-b border-white/5 flex-shrink-0">
          {[
            { id: "analysis", label: "AI Analysis", icon: Cpu },
            { id: "impact", label: "Impact", icon: GitMerge },
          ].map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setTab(id)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-display transition-colors ${tab === id ? "text-moss border-b-2 border-moss bg-moss/5" : "text-slate-500 hover:text-slate-300"
                }`}
            >
              <Icon size={11} />{label}
              {id === "impact" && impact.dependents.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 rounded-full bg-moss/20 text-moss text-[9px] font-bold">{impact.dependents.length}</span>
              )}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto">
          {tab === "analysis" && (
            <div className="p-5">
              {node.data.imports?.length > 0 && (
                <div className="mb-4">
                  <p className="text-[10px] uppercase tracking-wider text-slate-600 font-display mb-2">Imports</p>
                  <div className="flex flex-wrap gap-1.5 max-h-20 overflow-y-auto">
                    {node.data.imports.slice(0, 20).map((imp, i) => (
                      <span key={i} className="badge badge-gray text-[10px]">{imp.length > 25 ? "…" + imp.slice(-22) : imp}</span>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex items-center gap-2 mb-4">
                <div className="w-5 h-5 rounded bg-moss/15 flex items-center justify-center"><Cpu size={11} className="text-moss" /></div>
                <span className="text-xs font-display font-semibold text-moss uppercase tracking-wider">AI Analysis</span>
                {explanation?.cached && (
                  <span className="ml-auto flex items-center gap-1 text-[10px] text-moss/60" title="Loaded from cache"><Zap size={10} />cached</span>
                )}
              </div>
              {loading && <div className="flex items-center gap-3 text-slate-500"><Loader2 size={16} className="animate-spin text-moss" /><span className="text-sm">Analysing…</span></div>}
              {error && !loading && <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}
              {explanation && !loading && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="markdown-body">
                  {analysis && (
                    <div className="mb-6 space-y-4 p-3 rounded-xl bg-moss/5 border border-moss/10">
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-moss/60 font-display mb-1">Architectural Role</p>
                        <p className="text-sm text-slate-200 font-medium">{analysis.architectural_role}</p>
                      </div>

                      {analysis.key_patterns?.length > 0 && (
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-moss/60 font-display mb-1.5">Key Patterns</p>
                          <div className="flex flex-wrap gap-1">
                            {analysis.key_patterns.map((p, i) => (
                              <span key={i} className="px-1.5 py-0.5 rounded bg-moss/20 text-moss text-[10px] border border-moss/20">{p}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {analysis.concerns?.length > 0 && (
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-moss/60 font-display mb-1.5">Responsibilities & Concerns</p>
                          <ul className="list-disc list-inside space-y-0.5">
                            {analysis.concerns.map((c, i) => (
                              <li key={i} className="text-[11px] text-slate-400">{c}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                  <ReactMarkdown>{explanation.explanation}</ReactMarkdown>
                  {explanation.dependencies?.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/5">
                      <p className="text-[10px] uppercase tracking-wider text-slate-600 font-display mb-2">Detected Dependencies</p>
                      <div className="flex flex-wrap gap-1.5">
                        {explanation.dependencies.slice(0, 15).map((dep, i) => <span key={i} className="badge badge-moss text-[10px]">{dep}</span>)}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
              {chat.length > 0 && (
                <div className="mt-6 pt-4 border-t border-white/5 space-y-3">
                  {chat.map((msg, i) => (
                    <div key={i} className={`text-sm p-2 rounded-lg ${msg.role === "user" ? "bg-moss/20 text-slate-200 ml-6" : "bg-white/5 text-slate-300 mr-6"}`}>
                      <ReactMarkdown components={{ code({ inline, children }) { return inline ? <code className="bg-black/20 px-1 rounded">{children}</code> : <CodeBlock>{children}</CodeBlock>; } }}>{msg.content}</ReactMarkdown>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-4 pt-4 border-t border-white/5 flex gap-2">
                <input value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                  placeholder="Ask about this file..." className="flex-1 px-3 py-2 text-sm bg-charcoal-100/60 border border-white/10 rounded-lg outline-none text-slate-200" />
                <button onClick={sendMessage} disabled={chatLoading} className="px-3 py-2 bg-moss/30 rounded-lg text-xs hover:bg-moss/50 transition">
                  {chatLoading ? <Loader2 size={14} className="animate-spin" /> : "Ask"}
                </button>
              </div>
            </div>
          )}

          {tab === "impact" && (
            <div className="p-5 space-y-5">

              {impact.transitiveCount > 0 && (
                <div className="p-3 rounded-xl border border-amber-400/20 bg-amber-400/5 space-y-1">
                  <div className="flex items-center gap-2">
                    <TrendingUp size={13} className="text-amber-400 flex-shrink-0" />
                    <p className="text-xs font-display font-semibold text-amber-300">
                      {impact.transitiveCount} file{impact.transitiveCount !== 1 ? "s" : ""} could break
                    </p>
                  </div>
                  <p className="text-[11px] text-slate-500 leading-relaxed pl-5">
                    Changing this file could transitively affect{" "}
                    <span className="text-amber-400 font-semibold">{impact.transitiveCount}</span> file
                    {impact.transitiveCount !== 1 ? "s" : ""} up the dependency chain —{" "}
                    {impact.dependents.length} directly, {impact.transitiveCount - impact.dependents.length} transitively.
                  </p>
                </div>
              )}

              {impact.transitiveDepCount > 0 && (
                <div className="p-3 rounded-xl border border-slate-600/30 bg-white/3 space-y-1">
                  <div className="flex items-center gap-2">
                    <GitBranch size={12} className="text-slate-500 flex-shrink-0" />
                    <p className="text-[11px] text-slate-400">
                      Transitively depends on{" "}
                      <span className="text-moss font-semibold">{impact.transitiveDepCount}</span> file
                      {impact.transitiveDepCount !== 1 ? "s" : ""}{" "}
                      ({impact.dependencies.length} direct)
                    </p>
                  </div>
                </div>
              )}

              <div>
                <div className="flex items-center gap-2 mb-3">
                  <ArrowUpRight size={13} className="text-amber-400" />
                  <p className="text-xs font-display font-semibold text-amber-400 uppercase tracking-wider">Dependents</p>
                  <span className="text-[10px] text-slate-600">files that import this</span>
                </div>
                {impact.dependents.length === 0 ? (
                  <div className="p-4 rounded-lg bg-white/3 border border-white/8 text-center space-y-1">
                    <Ghost size={20} className="text-slate-600 mx-auto" />
                    <p className="text-xs text-slate-500">{isDeadCode ? "No file imports this — possible dead code or entry point" : "No dependents found"}</p>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    <p className="text-[10px] text-slate-600 mb-2">
                      Changing this could affect <span className="text-amber-400 font-semibold">{impact.dependents.length}</span> {impact.dependents.length === 1 ? "file" : "files"}:
                    </p>
                    {impact.dependents.map((n) => (
                      <button key={n.id} onClick={() => onJumpTo?.(n.id)}
                        className="w-full flex items-center gap-2.5 p-2 rounded-lg bg-white/3 border border-white/8 hover:bg-amber-400/5 hover:border-amber-400/20 transition-all text-left group">
                        <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: getLanguageColor(n.data?.language) }} />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-mono text-slate-300 truncate">{n.data?.label}</p>
                          <p className="text-[10px] text-slate-600 font-mono truncate">{n.data?.file_path}</p>
                        </div>
                        <ArrowUpRight size={11} className="text-slate-700 group-hover:text-amber-400 flex-shrink-0" />
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <div className="flex items-center gap-2 mb-3">
                  <GitBranch size={13} className="text-moss" />
                  <p className="text-xs font-display font-semibold text-moss uppercase tracking-wider">Dependencies</p>
                  <span className="text-[10px] text-slate-600">files this imports</span>
                </div>
                {impact.dependencies.length === 0 ? (
                  <div className="p-3 rounded-lg bg-white/3 border border-white/8 text-center">
                    <p className="text-xs text-slate-500">No local dependencies</p>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {impact.dependencies.map((n) => (
                      <button key={n.id} onClick={() => onJumpTo?.(n.id)}
                        className="w-full flex items-center gap-2.5 p-2 rounded-lg bg-white/3 border border-white/8 hover:bg-moss/5 hover:border-moss/20 transition-all text-left group">
                        <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: getLanguageColor(n.data?.language) }} />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-mono text-slate-300 truncate">{n.data?.label}</p>
                          <p className="text-[10px] text-slate-600 font-mono truncate">{n.data?.file_path}</p>
                        </div>
                        <ArrowUpRight size={11} className="text-slate-700 group-hover:text-moss flex-shrink-0" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}