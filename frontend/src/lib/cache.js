/**
 * Session-level API response cache with TTL.
 * Avoids redundant graph fetches when switching between views/repos.
 */

const DEFAULT_TTL_MS = 5 * 60 * 1000; // 5 minutes

export function getCached(key) {
  try {
    const raw = sessionStorage.getItem(`rscope:${key}`);
    if (!raw) return null;
    const { value, expiresAt } = JSON.parse(raw);
    if (Date.now() > expiresAt) {
      sessionStorage.removeItem(`rscope:${key}`);
      return null;
    }
    return value;
  } catch {
    return null;
  }
}

export function setCached(key, value, ttlMs = DEFAULT_TTL_MS) {
  try {
    sessionStorage.setItem(`rscope:${key}`, JSON.stringify({
      value,
      expiresAt: Date.now() + ttlMs,
    }));
  } catch {
    // Storage full — silently skip caching
  }
}

export function invalidateByPrefix(prefix) {
  try {
    const toRemove = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i);
      if (k?.startsWith(`rscope:${prefix}`)) toRemove.push(k);
    }
    toRemove.forEach((k) => sessionStorage.removeItem(k));
  } catch { /* ignore */ }
}
