import api from './axiosInstance'

export const chatbotService = {
  async listSessions({ companyId, customerUserId }) {
    const { data } = await api.get('/chat/sessions/', {
      params: {
        company_id: companyId,
        customer_user_id: customerUserId,
      },
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
