import { STORAGE_KEYS } from './constants'

/**
 * localStorage helpers for the public chat widget (`/chat/:companyId`).
 *
 * Visitors there are anonymous — there is no account and no token — so the
 * only thing tying a returning browser back to its conversation is the session
 * id the server handed out on the first message. It is scoped per company so
 * one browser can talk to several companies' widgets independently.
 */

const sessionKey = (companyId) => `${STORAGE_KEYS.CHAT_SESSION_ID}:${companyId}`

/** Reads a value, tolerating disabled/full storage (private mode, quotas). */
const read = (key) => {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

const write = (key, value) => {
  try {
    if (value === null || value === undefined) window.localStorage.removeItem(key)
    else window.localStorage.setItem(key, String(value))
  } catch {
    /* storage unavailable — the chat still works, it just won't survive a reload */
  }
}

export const getStoredSessionId = (companyId) => {
  const raw = read(sessionKey(companyId))
  const id = Number(raw)
  return raw && Number.isFinite(id) ? id : null
}

export const storeSessionId = (companyId, sessionId) =>
  write(sessionKey(companyId), sessionId)

export const clearStoredSessionId = (companyId) => write(sessionKey(companyId), null)

/** Optional name/email the visitor gave on the pre-chat form. */
export const getStoredGuest = () => {
  try {
    return JSON.parse(read(STORAGE_KEYS.CHAT_GUEST) || 'null')
  } catch {
    return null
  }
}

export const storeGuest = (guest) => {
  try {
    window.localStorage.setItem(STORAGE_KEYS.CHAT_GUEST, JSON.stringify(guest))
  } catch {
    /* ignore */
  }
}
