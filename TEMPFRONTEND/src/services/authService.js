import api from './axiosInstance'

/**
 * Auth + registration.
 *
 * Registration is one atomic call — `POST /auth/register/` creates the company
 * and its first Admin together, and returns a session. It replaced the old
 * two-step flow (POST /companies/ then POST /users/?user_type=Admin), which
 * only worked because user creation was publicly writable.
 *
 * Login and register carry `skipAuth` so a stale token in localStorage can't
 * make them fail with a 401 before the new session is issued.
 */
export const authService = {
  /** Create a company plus its Admin. Returns { token, expires_at, user, company }. */
  async register({ company, admin }) {
    const { data } = await api.post(
      '/auth/register/',
      { company, admin },
      { skipAuth: true },
    )
    return data
  },

  /** Log in with email + password. Returns { token, expires_at, user }. */
  async login(credentials) {
    const { data } = await api.post('/auth/login/', credentials, { skipAuth: true })
    return data
  },

  /** Revoke the current token server-side. */
  async logout() {
    await api.post('/auth/logout/')
  },

  /** The profile behind the stored token — used to validate it on app boot. */
  async me() {
    const { data } = await api.get('/auth/me/')
    return data
  },
}

export default authService
