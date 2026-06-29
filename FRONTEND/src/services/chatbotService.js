import axiosInstance from './axiosInstance'

/**
 * Chatbot endpoints (mounted under the `chatbot` app).
 *   GET    /chatbot/chatbots/
 *   POST   /chatbot/chatbots/
 *   PUT    /chatbot/chatbots/:id/
 *   DELETE /chatbot/chatbots/:id/
 */
const chatbotService = {
  list: async () => {
    const { data } = await axiosInstance.get('/chatbot/chatbots/')
    return data
  },

  create: async (payload) => {
    const { data } = await axiosInstance.post('/chatbot/chatbots/', payload)
    return data
  },

  update: async (id, payload) => {
    const { data } = await axiosInstance.put(`/chatbot/chatbots/${id}/`, payload)
    return data
  },

  remove: async (id) => {
    await axiosInstance.delete(`/chatbot/chatbots/${id}/`)
    return id
  },
}

export default chatbotService
