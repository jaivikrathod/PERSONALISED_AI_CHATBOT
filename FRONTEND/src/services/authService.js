import axiosInstance from './axiosInstance'

/**
 * Auth endpoints (Django backend: accounts app mounted at /api/v1/accounts/).
 *   POST /accounts/auth/login/          -> { access, refresh, user }
 *   POST /accounts/auth/token/refresh/  -> { access }
 *   GET  /accounts/users/me/            -> { success, user }
 *
 * NOTE: the backend exposes no logout endpoint (no token-blacklist view is
 * wired up), so logout() is a client-side-only token clear.
 */
const authService = {
  login: async (credentials) => {
    const { data } = await axiosInstance.post('/accounts/auth/login/', credentials)
    return data
  },

  refresh: async (refresh) => {
    const { data } = await axiosInstance.post('/accounts/auth/token/refresh/', {
      refresh,
    })
    return data
  },

  me: async () => {
    const { data } = await axiosInstance.get('/accounts/users/me/')
    // backend wraps the user in { success, user }
    return data.user ?? data
  },

  logout: async () => {
    // No server-side logout/blacklist endpoint exists on the backend; the
    // caller clears local tokens. Kept as a no-op for API symmetry.
  },
}

export default authService
