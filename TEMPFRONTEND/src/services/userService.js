import api from './axiosInstance'

/**
 * Company user management (`users.ManagedUserViewSet`).
 *
 * The old `?user_type=` and `?company_id=` parameters are gone: the server now
 * reads both the caller's role and their company from the bearer token, so
 * neither can be supplied by the client. Users are created into the caller's
 * own company automatically.
 *
 *   GET    /managed-users/
 *   POST   /managed-users/
 *   PUT    /managed-users/:id/
 *   DELETE /managed-users/:id/
 */
export const userService = {
  async list() {
    const { data } = await api.get('/managed-users/')
    return data
  },

  async create(payload) {
    const { data } = await api.post('/managed-users/', payload)
    return data
  },

  async update(id, payload) {
    const { data } = await api.put(`/managed-users/${id}/`, payload)
    return data
  },

  async remove(id) {
    await api.delete(`/managed-users/${id}/`)
    return id
  },
}

export default userService
