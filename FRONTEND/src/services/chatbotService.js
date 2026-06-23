import axiosInstance from './axiosInstance'

/**
 * Chatbot endpoints.
 *   GET    /chatbots/
 *   POST   /chatbots/
 *   PUT    /chatbots/:id/
 *   DELETE /chatbots/:id/
 */
const chatbotService = {
  list: async () => {    
    const { data } = await axiosInstance.get('/chatbots/')
    return data
  },

  create: async (payload) => {
    const { data } = await axiosInstance.post('/chatbots/', payload)
    return data
  },

  update: async (id, payload) => {
    const { data } = await axiosInstance.put(`/chatbots/${id}/`, payload)
    return data
  },

  remove: async (id) => {
    await axiosInstance.delete(`/chatbots/${id}/`)
    return id
  },
}

export default chatbotService
