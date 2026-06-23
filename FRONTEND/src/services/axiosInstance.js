import axios from 'axios'
import { API_BASE_URL } from '../utils/constants'
import { tokenStore } from '../utils/storage'

/**
 * Central axios instance.
 *  - Request interceptor attaches the JWT access token.
 *  - Response interceptor transparently refreshes an expired access token
 *    (SimpleJWT style: POST /auth/token/refresh/ { refresh } -> { access }).
 *  - Concurrent 401s are queued so we only refresh once.
 */
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// ---- request: attach bearer token --------------------------------------
axiosInstance.interceptors.request.use((config) => {
  const token = tokenStore.getAccess()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ---- response: refresh-on-401 ------------------------------------------
let isRefreshing = false
let pendingQueue = []

const processQueue = (error, token = null) => {
  pendingQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)))
  pendingQueue = []
}

// Allow the app to react to a hard logout (e.g. dispatch redux) without a
// circular import. authSlice registers a callback here.
let onAuthFailure = null
export const setAuthFailureHandler = (fn) => {
  onAuthFailure = fn
}

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status

    // Network / timeout — surface a friendly message
    if (!error.response) {
      return Promise.reject({
        message: 'Network error. Please check your connection.',
        original: error,
      })
    }

    const isRefreshCall = originalRequest?.url?.includes('token/refresh')

    if (status === 401 && !originalRequest._retry && !isRefreshCall) {
      const refresh = tokenStore.getRefresh()
      if (!refresh) {
        onAuthFailure?.()
        return Promise.reject(normalizeError(error))
      }

      if (isRefreshing) {
        // Queue until the in-flight refresh resolves
        return new Promise((resolve, reject) => {
          pendingQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return axiosInstance(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post(
          `${API_BASE_URL}/accounts/auth/token/refresh/`,
          { refresh },
          { headers: { 'Content-Type': 'application/json' } },
        )
        const newAccess = data.access
        tokenStore.setTokens({ access: newAccess, refresh: data.refresh })
        processQueue(null, newAccess)
        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        return axiosInstance(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        tokenStore.clear()
        onAuthFailure?.()
        return Promise.reject(normalizeError(refreshError))
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(normalizeError(error))
  },
)

/** Flatten a DRF / axios error into a single readable message. */
export function normalizeError(error) {
  const data = error.response?.data
  let message = 'Something went wrong.'

  if (typeof data === 'string') {
    message = data
  } else if (data?.detail) {
    message = data.detail
  } else if (data && typeof data === 'object') {
    // DRF field errors: { email: ["..."], password: ["..."] }
    const first = Object.values(data)[0]
    if (Array.isArray(first)) message = first[0]
    else if (typeof first === 'string') message = first
  } else if (error.message) {
    message = error.message
  }

  return { message, status: error.response?.status, data }
}

export default axiosInstance
