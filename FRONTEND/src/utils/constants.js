// Centralized config & enums.

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8000'

export const WIDGET_DOMAIN =
  import.meta.env.VITE_WIDGET_DOMAIN || 'https://yourdomain.com'

// localStorage keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'cs_access_token',
  REFRESH_TOKEN: 'cs_refresh_token',
  USER: 'cs_user',
  THEME: 'cs_theme',
}

export const CONVERSATION_STATUS = {
  OPEN: 'open',
  PENDING: 'pending',
  RESOLVED: 'resolved',
  ESCALATED: 'escalated',
}

export const CONVERSATION_STATUS_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: CONVERSATION_STATUS.OPEN, label: 'Open' },
  { value: CONVERSATION_STATUS.PENDING, label: 'Pending' },
  { value: CONVERSATION_STATUS.ESCALATED, label: 'Escalated' },
  { value: CONVERSATION_STATUS.RESOLVED, label: 'Resolved' },
]

export const CHATBOT_STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
}

export const DEFAULT_PAGE_SIZE = 10
