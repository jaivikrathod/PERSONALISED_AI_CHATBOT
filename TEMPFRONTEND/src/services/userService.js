import api from './axiosInstance'

/**
 * Company user management (`users.ManagedUserViewSet`).
 *
 * Every call carries `?user_type=<caller type>`: the backend
 * `IsAdminOrManager` permission reads it to authorize the request, and
 * `?company_id=` scopes the list to a single company.
 *
 *   GET    /managed-users/?company_id=&user_type=
 *   POST   /managed-users/?user_type=
 *   PUT    /managed-users/:id/?user_type=
 *   DELETE /managed-users/:id/?user_type=
 */
export const userService = {
  async list({ companyId, userType }) {
    const { data } = await api.get('/managed-users/', {
      params: { company_id: companyId, user_type: userType },
    })
    return data
  },

  async create(payload, { userType }) {
    const { data } = await api.post('/managed-users/', payload, {
      params: { user_type: userType },
    })
    return data
  },

  async update(id, payload, { userType }) {
    const { data } = await api.put(`/managed-users/${id}/`, payload, {
      params: { user_type: userType },
    })
    return data
  },

  async remove(id, { userType }) {
    await api.delete(`/managed-users/${id}/`, {
      params: { user_type: userType },
    })
    return id
  },
}

export default userService
