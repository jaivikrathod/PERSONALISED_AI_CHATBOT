import axiosInstance from './axiosInstance'

/**
 * Live-agent actions over a conversation.
 *   GET  /agents/                       -> list of agents (+ presence)
 *   POST /conversations/:id/take-over/
 *   POST /conversations/:id/assign/     { agent_id }
 *   POST /conversations/:id/transfer/   { agent_id }
 *   POST /conversations/:id/resolve/
 */
const agentService = {
  listAgents: async () => {
    const { data } = await axiosInstance.get('/agents/')
    return data
  },

  takeOver: async (conversationId) => {
    const { data } = await axiosInstance.post(
      `/conversations/${conversationId}/take-over/`,
    )
    return data
  },

  assign: async (conversationId, agentId) => {
    const { data } = await axiosInstance.post(
      `/conversations/${conversationId}/assign/`,
      { agent_id: agentId },
    )
    return data
  },

  transfer: async (conversationId, agentId) => {
    const { data } = await axiosInstance.post(
      `/conversations/${conversationId}/transfer/`,
      { agent_id: agentId },
    )
    return data
  },

  resolve: async (conversationId) => {
    const { data } = await axiosInstance.post(
      `/conversations/${conversationId}/resolve/`,
    )
    return data
  },
}

export default agentService
