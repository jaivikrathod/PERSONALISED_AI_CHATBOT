import { STORAGE_KEYS } from './constants'

// Thin, safe localStorage wrapper — private mode / quota errors never throw.
export const storage = {
  get(key) {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value)
    } catch {
      /* ignore quota / private-mode errors */
    }
  },
  remove(key) {
    try {
      localStorage.removeItem(key)
    } catch {
      /* noop */
    }
  },
  getJSON(key) {
    const raw = this.get(key)
    if (!raw) return null
    try {
      return JSON.parse(raw)
    } catch {
      return null
    }
  },
  setJSON(key, value) {
    this.set(key, JSON.stringify(value))
  },
}

/**
 * Persists the logged-in user. There is no JWT in this app — the backend
 * login endpoint returns the user profile, which we store to gate the UI.
 * Swap this for token storage when real auth is added.
 */
export const userStore = {
  get: () => storage.getJSON(STORAGE_KEYS.USER),
  set: (user) => storage.setJSON(STORAGE_KEYS.USER, user),
  clear: () => storage.remove(STORAGE_KEYS.USER),
}

export const chatSessionStore = {
  get: () => storage.get(STORAGE_KEYS.CHAT_SESSION_ID),
  set: (sessionId) => storage.set(STORAGE_KEYS.CHAT_SESSION_ID, String(sessionId)),
  clear: () => storage.remove(STORAGE_KEYS.CHAT_SESSION_ID),
}
