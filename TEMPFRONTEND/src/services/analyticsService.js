import axiosInstance from './axiosInstance'

/**
 * Dashboard + analytics endpoints.
 *   GET /analytics/overview/?from=&to=
 *   GET /analytics/conversations-series/?from=&to=&granularity=day|week
 *   GET /analytics/top-faqs/
 *   GET /analytics/unanswered/?page=
 *   POST /analytics/unanswered/:id/convert/   -> creates FAQ
 */
const analyticsService = {
  overview: async ({ from, to } = {}) => {
    const { data } = await axiosInstance.get('/analytics/overview/', {
      params: { from, to },
    })
    return data
  },

  conversationsSeries: async ({ from, to, granularity = 'day' } = {}) => {
    const { data } = await axiosInstance.get('/analytics/conversations-series/', {
      params: { from, to, granularity },
    })
    return data
  },

  topFaqs: async () => {
    const { data } = await axiosInstance.get('/analytics/top-faqs/')
    return data
  },

  unanswered: async ({ page = 1 } = {}) => {
    const { data } = await axiosInstance.get('/analytics/unanswered/', {
      params: { page },
    })
    return data
  },

  convertUnanswered: async (id, payload) => {
    const { data } = await axiosInstance.post(
      `/analytics/unanswered/${id}/convert/`,
      payload,
    )
    return data
  },
}

export default analyticsService
