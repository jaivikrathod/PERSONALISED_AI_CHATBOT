import axios from 'axios'
import { API_BASE_URL } from '../utils/constants'
import { clearSession, tokenStore } from '../utils/storage'

/**
 * Central axios instance for all API calls.
 *
 * The API is closed by default: every endpoint except registration, login and
 * the public chat widget requires the bearer token issued at login, which the
 * request interceptor below attaches to every call.
 */
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Read the token per request rather than capturing it once: login, logout and
// expiry all change it while the module stays loaded.
axiosInstance.interceptors.request.use((config) => {
  const token = tokenStore.get()
  if (token && !config.skipAuth) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Flatten a DRF / axios error into a single readable message.
export function normalizeError(error) {
  const data = error.response?.data
  let message = 'Something went wrong.'

  if (!error.response) {
    message = 'Network error. Is the API server running?'
  } else if (typeof data === 'string') {
    message = data
  } else if (data?.error) {
    message = data.error
  } else if (data?.detail) {
    message = data.detail
  } else if (data && typeof data === 'object') {
    // DRF field errors: { email: ["..."], password: ["..."] }
    const [firstKey] = Object.keys(data)
    const first = data[firstKey]
    if (Array.isArray(first)) message = `${firstKey}: ${first[0]}`
    else if (typeof first === 'string') message = first
  } else if (error.message) {
    message = error.message
  }

  return { message, status: error.response?.status, data }
}

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    // An expired or revoked token can't be recovered from in-page. Drop the
    // stale session and send the user to login, preserving where they were.
    // The public chat widget is unauthenticated, so it is left alone.
    const isAuthCall = error.config?.skipAuth
    const onPublicChat = window.location.pathname.startsWith('/chat/')
    if (error.response?.status === 401 && !isAuthCall && !onPublicChat) {
      clearSession()
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(normalizeError(error))
  },
)

export default axiosInstance
