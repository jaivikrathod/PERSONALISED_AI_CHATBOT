import api from './axiosInstance'
import { USER_TYPES } from '../utils/constants'

/**
 * Auth + registration API calls.
 *
 * Registration is a two-step flow against the existing CRUD endpoints:
 *   1. POST /companies/                  -> create the company
 *   2. POST /users/?user_type=Admin      -> create the Admin user for it
 *
 * The `user_type` query param is what the backend `IsAdminOrManager`
 * permission on `users.UserViewSet` inspects (see users/permissions.py); the
 * request is rejected with 403 without it.
 */
export const authService = {
  /** Create a company. Returns the created company (with `id`). */
  async createCompany(company) {
    const { data } = await api.post('/companies/', company)
    return data
  },

  /** Create an Admin user tied to a company. */
  async createAdminUser(user) {
    const { data } = await api.post(
      '/users/',
      { ...user, type: USER_TYPES.ADMIN },
      { params: { user_type: USER_TYPES.ADMIN } },
    )
    return data
  },

  /**
   * Full registration: create the company, then its admin user.
   * If user creation fails we surface the error (the company will already
   * exist — acceptable for this demo flow).
   */
  async register({ company, admin }) {
    const createdCompany = await this.createCompany(company)
    const createdAdmin = await this.createAdminUser({
      ...admin,
      company: createdCompany.id,
    })
    return { company: createdCompany, admin: createdAdmin }
  },

  /** Log in with email + password. Returns the user profile. */
  async login(credentials) {
    const { data } = await api.post('/auth/login/', credentials)
    return data
  },
}

export default authService
