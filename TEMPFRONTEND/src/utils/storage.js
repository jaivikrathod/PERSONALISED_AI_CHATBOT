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
 * The bearer token issued by `POST /auth/login/`. This is what actually grants
 * access — every API call carries it, and clearing it ends the session.
 */
export const tokenStore = {
  get: () => storage.get(STORAGE_KEYS.TOKEN),
  set: (token) => storage.set(STORAGE_KEYS.TOKEN, token),
  clear: () => storage.remove(STORAGE_KEYS.TOKEN),
}

/**
 * Cached profile for the signed-in user. Display only — the token above is the
 * credential, and `GET /auth/me/` is the authority on who the user is.
 */
export const userStore = {
  get: () => storage.getJSON(STORAGE_KEYS.USER),
  set: (user) => storage.setJSON(STORAGE_KEYS.USER, user),
  clear: () => storage.remove(STORAGE_KEYS.USER),
}

/** Clears everything that identifies the current session. */
export const clearSession = () => {
  tokenStore.clear()
  userStore.clear()
}
