import { useEffect, useCallback } from "react";

/**
 * Global keyboard shortcut handler for RepoScope AI graph view.
 * @param {Object} actions - { fitView, toggleSemantic, toggleChat, focusSearch }
 */
export function useKeyboardShortcuts({ fitView, toggleSemantic, toggleChat, focusSearch } = {}) {
  const handler = useCallback((e) => {
    const tag = document.activeElement?.tagName?.toLowerCase();
    const isInput = tag === "input" || tag === "textarea" || tag === "select";

    // Cmd/Ctrl+K — focus search
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      focusSearch?.();
      return;
    }

    // Skip single-key shortcuts when an input is focused
    if (isInput) return;

    switch (e.key) {
      case "Escape":
        // Handled by individual panels via their own escape listeners
        break;
      case "f":
      case "F":
        e.preventDefault();
        fitView?.();
        break;
      case "s":
      case "S":
        e.preventDefault();
        toggleSemantic?.();
        break;
      case "c":
      case "C":
        e.preventDefault();
        toggleChat?.();
        break;
      default:
        break;
    }
  }, [fitView, toggleSemantic, toggleChat, focusSearch]);

  useEffect(() => {
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handler]);
}
