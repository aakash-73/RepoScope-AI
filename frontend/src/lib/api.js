import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 120000,
});

export async function listRepos() {
  const { data } = await api.get("/repos");
  return data;
}

export async function importRepo(githubUrl, branch = "main") {
  const { data } = await api.post("/import", { github_url: githubUrl, branch });
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

export async function fetchGraph(repoId) {
  const { data } = await api.get(`/graph/${repoId}`);
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