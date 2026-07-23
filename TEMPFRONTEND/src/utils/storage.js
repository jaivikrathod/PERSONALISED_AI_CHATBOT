import { STORAGE_KEYS } from './constants'

/**
 * Persists the logged-in user in localStorage. There is no JWT in this app —
 * the backend login endpoint returns the user profile which we store to gate
 * the UI. Swap this for token storage when real auth is added.
 */
export const userStore = {
  get() {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.USER)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  },
  set(user) {
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user))
  },
  clear() {
    localStorage.removeItem(STORAGE_KEYS.USER)
  },
}

export const chatSessionStore = {
  get() {
    try {
      return localStorage.getItem(STORAGE_KEYS.CHAT_SESSION_ID)
    } catch {
      return null
    }
  },
  set(sessionId) {
    localStorage.setItem(STORAGE_KEYS.CHAT_SESSION_ID, String(sessionId))
  },
  clear() {
    localStorage.removeItem(STORAGE_KEYS.CHAT_SESSION_ID)
  },
}
