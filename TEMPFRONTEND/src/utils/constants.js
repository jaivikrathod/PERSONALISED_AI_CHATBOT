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
  THEME: 've_theme',
}

// User types supported by the backend `users.User` model.
export const USER_TYPES = {
  ADMIN: 'Admin',
  AGENT: 'Agent',
  MANAGER: 'Manager',
}

// Types allowed to reach the user-management CRUD. Mirrors the backend
// `IsAdminOrManager` permission, which reads the `?user_type=` query param.
export const MANAGER_TYPES = [USER_TYPES.ADMIN, USER_TYPES.MANAGER]

export const USER_TYPE_OPTIONS = [
  { value: USER_TYPES.AGENT, label: 'Agent' },
  { value: USER_TYPES.MANAGER, label: 'Manager' },
  { value: USER_TYPES.ADMIN, label: 'Admin' },
]

// Gender choices supported by the backend.
export const GENDER_OPTIONS = [
  { value: 'Male', label: 'Male' },
  { value: 'Female', label: 'Female' },
  { value: 'Other', label: 'Other' },
]

// `chat.ChatSession.Status` values.
export const SESSION_STATUS = {
  OPEN: 'open',
  IN_PROGRESS: 'in_progress',
  CLOSED: 'closed',
}

// Badge tone per session status (tones are defined in components/ui/Badge).
export const SESSION_STATUS_TONE = {
  [SESSION_STATUS.OPEN]: 'blue',
  [SESSION_STATUS.IN_PROGRESS]: 'green',
  [SESSION_STATUS.CLOSED]: 'gray',
}

export const SESSION_STATUS_LABEL = {
  [SESSION_STATUS.OPEN]: 'Open',
  [SESSION_STATUS.IN_PROGRESS]: 'In progress',
  [SESSION_STATUS.CLOSED]: 'Closed',
}

// Socket lifecycle, shared by the customer widget and the agent console.
export const SOCKET_STATUS = {
  CONNECTING: 'connecting',
  OPEN: 'open',
  CLOSED: 'closed',
}
