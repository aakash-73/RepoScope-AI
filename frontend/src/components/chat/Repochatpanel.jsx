import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";
import {
    X, Loader2, Send, Bot, User,
    Sparkles, Copy, Check, RotateCcw,
} from "lucide-react";
import { fetchRepoSummary, chatWithRepo } from "../../lib/api";

function CodeBlock({ children }) {
    const [copied, setCopied] = useState(false);
    const code = Array.isArray(children) ? children.join("") : children;

    return (
        <span className="block bg-black/30 rounded-lg overflow-hidden my-2">
            <span className="flex justify-end px-2 py-1 border-b border-white/10">
                <button
                    onClick={() => {
                        navigator.clipboard.writeText(code);
                        setCopied(true);
                        setTimeout(() => setCopied(false), 2000);
                    }}
                    className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
                >
                    {copied ? <Check size={10} /> : <Copy size={10} />}
                    {copied ? "Copied" : "Copy"}
                </button>
            </span>
            <span className="block p-3 text-xs overflow-auto text-slate-300 whitespace-pre">
                <code>{code}</code>
            </span>
        </span>
    );
}

const mdComponents = {
    pre({ children }) {
        const codeText = children?.props?.children || children;
        return <CodeBlock>{codeText}</CodeBlock>;
    },
    code({ className, children, node, ...props }) {
        const match = /language-(\w+)/.exec(className || '');
        const text = String(children);
        const isBlock = match || text.includes('\n');
        
        if (!isBlock) {
            return (
                <code className="bg-moss/15 text-moss px-1 py-0.5 rounded text-xs font-mono" {...props}>
                    {children}
                </code>
            );
        }
        return <CodeBlock>{children}</CodeBlock>;
    },
    p({ children }) {
        return <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>;
    },
    ul({ children }) {
        return <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>;
    },
    ol({ children }) {
        return <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>;
    },
    li({ children }) {
        return <li className="text-slate-300">{children}</li>;
    },
    strong({ children }) {
        return <strong className="text-slate-100 font-semibold">{children}</strong>;
    },
    h3({ children }) {
        return <h3 className="text-slate-200 font-semibold text-sm mt-3 mb-1">{children}</h3>;
    },
};

function Message({ msg }) {
    const isUser = msg.role === "user";
    return (
        <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex gap-2.5 ${isUser ? "flex-row-reverse" : "flex-row"}`}
        >
            <div
                className={`
                    w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5
                    ${isUser ? "bg-moss/20 border border-moss/30" : "bg-white/5 border border-white/10"}
                `}
            >
                {isUser
                    ? <User size={11} className="text-moss" />
                    : <Bot size={11} className="text-slate-400" />
                }
            </div>
            <div
                className={`
                    max-w-[85%] rounded-2xl px-3 py-2.5 text-sm
                    ${isUser
                        ? "bg-moss/15 border border-moss/20 text-slate-200 rounded-tr-sm"
                        : "bg-white/5 border border-white/8 text-slate-300 rounded-tl-sm"
                    }
                `}
            >
                {isUser ? (
                    <p className="leading-relaxed">{msg.content}</p>
                ) : (
                    <ReactMarkdown components={mdComponents}>
                        {msg.content}
                    </ReactMarkdown>
                )}
            </div>
        </motion.div>
    );
}

function TypingIndicator() {
    return (
        <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-2.5"
        >
            <div className="w-6 h-6 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
                <Bot size={11} className="text-slate-400" />
            </div>
            <div className="bg-white/5 border border-white/8 rounded-2xl rounded-tl-sm px-3 py-3 flex items-center gap-1">
                {[0, 1, 2].map((i) => (
                    <motion.div
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-slate-500"
                        animate={{ y: [0, -4, 0] }}
                        transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                    />
                ))}
            </div>
        </motion.div>
    );
}

// RepoChatPanel no longer owns its trigger button — that now lives in GraphCanvas
// anchored above the minimap. This component only renders the chat panel itself.
// Props:
//   open       — boolean, controlled by parent (GraphPage)
//   onClose    — called when the user closes the panel
//   repoId     — current repo id
//   repoName   — display name
export default function RepoChatPanel({ open, onClose, repoId, repoName }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [summaryLoading, setSummaryLoading] = useState(false);
    const [error, setError] = useState(null);
    const bottomRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    useEffect(() => {
        if (open) setTimeout(() => inputRef.current?.focus(), 150);
    }, [open]);

    // Load summary the first time the panel opens for this repo
    useEffect(() => {
        if (!open || !repoId || messages.length > 0) return;
        loadSummary();
    }, [open, repoId]);

    // Reset conversation when repo changes
    useEffect(() => {
        setMessages([]);
        setError(null);
    }, [repoId]);

    async function loadSummary() {
        setSummaryLoading(true);
        setError(null);
        try {
            const res = await fetchRepoSummary(repoId);
            setMessages([{ role: "assistant", content: res.summary }]);
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to load repo summary.");
        } finally {
            setSummaryLoading(false);
        }
    }

    async function sendMessage() {
        const text = input.trim();
        if (!text || loading) return;

        const userMsg = { role: "user", content: text };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setLoading(true);
        setError(null);
        const history = messages.map((m) => ({ role: m.role, content: m.content }));

        try {
            const res = await chatWithRepo(repoId, text, history);
            setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
        } catch (err) {
            setError(err.response?.data?.detail || "Chat failed. Please try again.");
        } finally {
            setLoading(false);
        }
    }

    const handleKey = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    if (!repoId) return null;

    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    key="panel"
                    initial={{ opacity: 0, y: 24, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 24, scale: 0.96 }}
                    transition={{ type: "spring", damping: 28, stiffness: 320 }}
                    // Anchored to bottom-right to sit above the minimap area
                    className="absolute bottom-36 right-6 z-30 w-[400px] h-[520px] flex flex-col glass rounded-2xl overflow-hidden shadow-2xl"
                >
                    {/* Header */}
                    <div className="px-4 py-3.5 border-b border-white/5 flex items-center gap-3 flex-shrink-0">
                        <div className="w-7 h-7 rounded-lg bg-moss/15 border border-moss/20 flex items-center justify-center">
                            <Sparkles size={13} className="text-moss" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-display font-semibold text-slate-200 leading-tight">
                                Repo Chat
                            </p>
                            <p className="text-[11px] text-slate-600 font-mono truncate">
                                {repoName}
                            </p>
                        </div>
                        <div className="flex items-center gap-1">
                            <button
                                onClick={() => { setMessages([]); loadSummary(); }}
                                disabled={summaryLoading}
                                title="Reset conversation"
                                className="p-1.5 rounded-lg hover:bg-white/5 text-slate-600 hover:text-slate-400 transition-colors"
                            >
                                <RotateCcw size={13} />
                            </button>
                            <button
                                onClick={onClose}
                                className="p-1.5 rounded-lg hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
                            >
                                <X size={15} />
                            </button>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                        {summaryLoading && messages.length === 0 && (
                            <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
                                <Loader2 size={22} className="animate-spin text-moss" />
                                <p className="text-sm font-display">Analysing repository…</p>
                            </div>
                        )}

                        {error && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
                            >
                                {error}
                            </motion.div>
                        )}

                        {messages.map((msg, i) => (
                            <Message key={i} msg={msg} />
                        ))}

                        {loading && <TypingIndicator />}
                        <div ref={bottomRef} />
                    </div>

                    {/* Quick prompts */}
                    {messages.length === 1 && !loading && (
                        <div className="px-4 pb-2 flex gap-2 overflow-x-auto flex-shrink-0">
                            {[
                                "What's the tech stack?",
                                "How does data flow?",
                                "What are the main entry points?",
                            ].map((prompt) => (
                                <button
                                    key={prompt}
                                    onClick={() => { setInput(prompt); inputRef.current?.focus(); }}
                                    className="flex-shrink-0 text-[11px] px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-slate-400 hover:text-slate-200 hover:border-moss/30 transition-all whitespace-nowrap"
                                >
                                    {prompt}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Input */}
                    <div className="px-3 pb-3 pt-2 border-t border-white/5 flex-shrink-0">
                        <div className="flex gap-2 items-end">
                            <textarea
                                ref={inputRef}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKey}
                                placeholder="Ask anything about this repo…"
                                rows={1}
                                className="flex-1 resize-none px-3 py-2.5 text-sm bg-charcoal-100/60 border border-white/10 rounded-xl outline-none text-slate-200 placeholder-slate-600 focus:border-moss/30 transition-colors leading-relaxed"
                                style={{ maxHeight: "96px" }}
                                onInput={(e) => {
                                    e.target.style.height = "auto";
                                    e.target.style.height = Math.min(e.target.scrollHeight, 96) + "px";
                                }}
                                disabled={summaryLoading}
                            />
                            <button
                                onClick={sendMessage}
                                disabled={loading || summaryLoading || !input.trim()}
                                className="w-9 h-9 flex-shrink-0 rounded-xl bg-moss/30 hover:bg-moss/50 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
                            >
                                {loading
                                    ? <Loader2 size={14} className="animate-spin text-moss" />
                                    : <Send size={14} className="text-moss" />
                                }
                            </button>
                        </div>
                        <p className="text-[10px] text-slate-700 mt-1.5 px-1">
                            Powered by Llama 3.1 8B · Enter to send
                        </p>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}