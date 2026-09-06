import api from './axiosInstance'

/**
 * REST side of the public chat widget. Both endpoints are open — the widget is
 * served to anonymous visitors at `/chat/:companyId`.
 */
export const chatbotService = {
  /** Public company metadata (name only) used to brand the widget. */
  async getWidgetConfig({ companyId }) {
    const { data } = await api.get('/chat/widget/', {
      params: { company_id: companyId },
    })
    return data
  },

  async getHistory({ sessionId, companyId }) {
    const { data } = await api.get('/chat/history/', {
      params: {
        session_id: sessionId,
        company_id: companyId,
      },
    })
    return data
  },
}

export default chatbotService
