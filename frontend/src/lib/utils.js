import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export const LANGUAGE_COLORS = {
  python: "#3572A5",
  javascript: "#F7DF1E",
  typescript: "#3178C6",
  java: "#B07219",
  go: "#00ADD8",
  rust: "#DEA584",
  cpp: "#F34B7D",
  c: "#555555",
  csharp: "#239120",
  ruby: "#701516",
  php: "#4F5D95",
  swift: "#FA7343",
  kotlin: "#A97BFF",
  vue: "#41B883",
  svelte: "#FF3E00",
  html: "#E34C26",
  css: "#563D7C",
  scss: "#C6538C",
  json: "#8BC34A",
  yaml: "#CB171E",
  markdown: "#9CA3AF",
  unknown: "#4B5563",
};

export function getLanguageColor(lang) {
  return LANGUAGE_COLORS[lang] || LANGUAGE_COLORS.unknown;
}

export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}
