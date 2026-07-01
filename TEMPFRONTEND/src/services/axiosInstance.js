import axios from 'axios'
import { API_BASE_URL } from '../utils/constants'

/**
 * Central axios instance for all API calls.
 * The backend endpoints are currently open (no auth token required), so this
 * is intentionally simple: a base URL + JSON headers + error normalization.
 */
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
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

// Reject with a normalized error so callers get a consistent { message } shape.
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(normalizeError(error)),
)

export default axiosInstance
