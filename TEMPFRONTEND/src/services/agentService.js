import api from './axiosInstance'

/**
 * REST side of the agent console. The live updates arrive over the
 * `ws/agent/` socket; these calls are used for the initial load and as a
 * fallback when the socket is down.
 */
export const agentService = {
  async listChats(agentId) {
    const { data } = await api.get('/agent/chats/', {
      params: { agent_id: agentId },
    })
    return data
  },

  async getHistory({ agentId, sessionId }) {
    const { data } = await api.get('/agent/chats/history/', {
      params: { agent_id: agentId, session_id: sessionId },
    })
    return data
  },

  async sendMessage({ agentId, sessionId, message }) {
    const { data } = await api.post('/agent/chats/send/', {
      agent_id: agentId,
      session_id: sessionId,
      message,
    })
    return data
  },

  async closeChat({ agentId, sessionId }) {
    const { data } = await api.post('/agent/chats/close/', {
      agent_id: agentId,
      session_id: sessionId,
    })
    return data
  },
}

export default agentService
