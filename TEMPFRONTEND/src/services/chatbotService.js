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

  /**
   * Replay one conversation. The session's `token` is required: without it a
   * visitor could read any other visitor's chat by guessing a session id.
   */
  async getHistory({ sessionId, token }) {
    const { data } = await api.get('/chat/history/', {
      params: { session_id: sessionId, token },
    })
    return data
  },
}

export default chatbotService
