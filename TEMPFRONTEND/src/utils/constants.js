// Centralized config & enums.

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

// localStorage keys
export const STORAGE_KEYS = {
  USER: 've_user',
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
