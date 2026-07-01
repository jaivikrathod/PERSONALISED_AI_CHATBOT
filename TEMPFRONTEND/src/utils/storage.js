import { STORAGE_KEYS } from './constants'

// Thin, safe localStorage wrapper used by auth + theme.

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

// Auth token helpers (used by axios interceptors & authSlice)
export const tokenStore = {
  getAccess: () => storage.get(STORAGE_KEYS.ACCESS_TOKEN),
  getRefresh: () => storage.get(STORAGE_KEYS.REFRESH_TOKEN),
  setTokens: ({ access, refresh }) => {
    if (access) storage.set(STORAGE_KEYS.ACCESS_TOKEN, access)
    if (refresh) storage.set(STORAGE_KEYS.REFRESH_TOKEN, refresh)
  },
  clear: () => {
    storage.remove(STORAGE_KEYS.ACCESS_TOKEN)
    storage.remove(STORAGE_KEYS.REFRESH_TOKEN)
    storage.remove(STORAGE_KEYS.USER)
  },
}
