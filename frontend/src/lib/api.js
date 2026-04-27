import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "";

/**
 * Retrieves the browser-specific client ID from localStorage,
 * or generates a new one if it doesn't exist.
 */
export function getClientId() {
  let id = localStorage.getItem("reposcope_client_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("reposcope_client_id", id);
  }
  return id;
}

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  timeout: 120000,
});

// Automatically include the client ID in every request
api.interceptors.request.use((config) => {
  const clientId = getClientId();
  if (clientId) {
    config.headers["X-Client-ID"] = clientId;
  }
  return config;
});

export async function listRepos() {
  const { data } = await api.get("/repos");
  return data;
}

export async function importRepo(githubUrl, branch = "main") {
  const clientId = getClientId();
  const { data } = await api.post("/import", {
    github_url: githubUrl,
    branch,
    client_id: clientId,
  });
  return data;
}

export async function deleteRepo(repoId) {
  const { data } = await api.delete(`/repos/${repoId}`);
  return data;
}

export async function retryRepoImport(repoId) {
  const { data } = await api.post(`/repos/${repoId}/retry`);
  return data;
}

export async function fetchGraph(repoId, viewType = "structure") {
  const { data } = await api.get(`/graph/${repoId}`, {
    params: { view_type: viewType },
  });
  return data;
}

export async function explainComponent(repoId, filePath) {
  const { data } = await api.post("/explain", {
    repo_id: repoId,
    file_path: filePath,
  });
  return data;
}

export async function chatComponent(repoId, filePath, message, history) {
  const res = await api.post("/component/chat", {
    repo_id: repoId,
    file_path: filePath,
    query: message,
    history,
  });
  return res.data;
}

export async function fetchChatHistory(repoId) {
  const { data } = await api.get(`/repo/${repoId}/chat/history`);
  return data;
}

export async function clearChatHistory(repoId) {
  const { data } = await api.delete(`/repo/${repoId}/chat/history`);
  return data;
}

export async function fetchProactiveInsights(repoId) {
  const { data } = await api.get(`/repo/${repoId}/insights`);
  return data;
}

export async function fetchRepoSummary(repoId) {
  const { data } = await api.get(`/repo/${repoId}/summary`);
  return data;
}

export async function chatWithRepo(repoId, query, history = []) {
  const { data } = await api.post(`/repo/${repoId}/chat`, { query, history });
  return data;
}

export async function fetchLanguages(repoId) {
  const { data } = await api.get("/languages", {
    params: repoId ? { repo_id: repoId } : {},
  });
  return data.languages;
}

export async function updateLanguageColor(key, color, repoId) {
  const { data } = await api.patch(
    `/languages/${encodeURIComponent(key)}`,
    { color },
    { params: repoId ? { repo_id: repoId } : {} }
  );
  return data;
}

export async function fetchAnalysisStatus(repoId) {
  const { data } = await api.get(`/analysis/${repoId}/status`);
  return data;
}

export async function fetchRepoAnalysis(repoId) {
  const { data } = await api.get(`/analysis/${repoId}/repo`);
  return data;
}

export async function fetchNodeAnalysis(repoId, filePath) {
  const { data } = await api.get(`/analysis/${repoId}/node`, {
    params: { file_path: filePath },
  });
  return data;
}

export async function reanalyzeNode(repoId, filePath) {
  const { data } = await api.post(`/analysis/${repoId}/node/reanalyze`, {
    file_path: filePath,
  });
  return data;
}

export const syncRepo = async (repoId) => {
  const { data } = await api.post(`/repos/${repoId}/sync`);
  return data;
};

export async function updateSyncSettings(repoId, settings) {
  const { data } = await api.patch(`/repos/${repoId}/sync-settings`, settings);
  return data;
}

export async function getFileContent(repoId, filePath) {
  const { data } = await api.get(`/repo/${repoId}/file/content`, {
    params: { file_path: filePath },
  });
  return data;
}

/**
 * Streams repo chat response token-by-token.
 * onChunk(token: string) is called for each text chunk.
 * onDone() is called when streaming finishes.
 * Returns a controller so callers can abort.
 */
export function streamChatWithRepo(repoId, query, history, onChunk, onDone, onError) {
  const controller = new AbortController();

  (async () => {
    try {
      const resp = await fetch(`/api/v1/repo/${repoId}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, history }),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        onError?.(err.detail || "Stream failed");
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE format: each event is "data: {...}\n\n"
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          const raw = line.slice(5).trim();
          if (raw === "[DONE]") { onDone?.(); return; }
          try {
            const parsed = JSON.parse(raw);
            if (parsed.token) onChunk(parsed.token);
            if (parsed.error) onError?.(parsed.error);
          } catch { /* ignore malformed chunks */ }
        }
      }
      onDone?.();
    } catch (err) {
      if (err.name !== "AbortError") onError?.(err.message);
    }
  })();

  return controller;
}