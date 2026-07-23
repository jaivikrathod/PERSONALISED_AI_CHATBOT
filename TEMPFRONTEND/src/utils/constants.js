// Centralized config & enums.

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

// WebSocket origin for the chatbot socket. Derived from the API base URL by
// swapping the scheme (http->ws / https->wss) and dropping the /api suffix,
// so it tracks the API host without a second env var in most setups.
export const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL ||
  API_BASE_URL.replace(/^http/, 'ws').replace(/\/api\/?$/, '')

// localStorage keys
export const STORAGE_KEYS = {
  USER: 've_user',
  CHAT_SESSION_ID: 've_chat_session_id',
}

// User types supported by the backend `users.User` model.
export const USER_TYPES = {
  ADMIN: 'Admin',
  EMPLOYEE: 'Employee',
  MANAGER: 'Manager',
}

// Gender choices supported by the backend.
export const GENDER_OPTIONS = [
  { value: 'Male', label: 'Male' },
  { value: 'Female', label: 'Female' },
  { value: 'Other', label: 'Other' },
]
