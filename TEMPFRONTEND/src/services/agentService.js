import api from './axiosInstance'

/**
 * REST side of the agent console. The live updates arrive over the
 * `ws/agent/` socket; these calls are used for the initial load and as a
 * fallback when the socket is down.
 *
 * None of these take an agent id any more: the server reads the agent from the
 * bearer token, so an agent can only ever act as themselves.
 */
export const agentService = {
  async listChats() {
    const { data } = await api.get('/agent/chats/')
    return data
  },

  async getHistory({ sessionId }) {
    const { data } = await api.get('/agent/chats/history/', {
      params: { session_id: sessionId },
    })
    return data
  },

  async sendMessage({ sessionId, message }) {
    const { data } = await api.post('/agent/chats/send/', {
      session_id: sessionId,
      message,
    })
    return data
  },

  async closeChat({ sessionId }) {
    const { data } = await api.post('/agent/chats/close/', {
      session_id: sessionId,
    })
    return data
  },
}

export default agentService
