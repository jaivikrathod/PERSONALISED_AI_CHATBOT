import axiosInstance from './axiosInstance'

/**
 * Conversations & messages.
 *   GET  /conversations/?search=&status=&page=
 *   GET  /conversations/:id/
 *   GET  /conversations/:id/messages/?before=<cursor>
 *   POST /conversations/:id/messages/   { body }
 *   PATCH /conversations/:id/           { status, assignee }
 */
const conversationService = {
  list: async ({ search = '', status = 'all', page = 1 } = {}) => {
    const { data } = await axiosInstance.get('/conversations/', {
      params: { search, status: status === 'all' ? undefined : status, page },
    })
    return data
  },

  get: async (id) => {
    const { data } = await axiosInstance.get(`/conversations/${id}/`)
    return data
  },

  getMessages: async (id, { before } = {}) => {
    const { data } = await axiosInstance.get(`/conversations/${id}/messages/`, {
      params: { before },
    })
    return data
  },

  sendMessage: async (id, body) => {
    const { data } = await axiosInstance.post(
      `/conversations/${id}/messages/`,
      { body },
    )
    return data
  },

  updateStatus: async (id, status) => {
    const { data } = await axiosInstance.patch(`/conversations/${id}/`, { status })
    return data
  },
}

export default conversationService
