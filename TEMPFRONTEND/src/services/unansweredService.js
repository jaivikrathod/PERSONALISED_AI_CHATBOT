import api from './axiosInstance'

/** Calls for the "unanswered messages" inbox (questions the FAQ couldn't answer). */
export const unansweredService = {
  /** List unanswered messages for a company. */
  async list(companyId) {
    const { data } = await api.get('/unanswered-messages/', {
      params: { company_id: companyId },
    })
    return data
  },

  /**
   * Provide an answer for an unanswered message. The backend creates a
   * Question from it, vectorizes it, and removes it from the inbox.
   */
  async resolve(id, answer) {
    const { data } = await api.post(`/unanswered-messages/${id}/resolve/`, {
      answer,
    })
    return data
  },

  /** Dismiss an unanswered message without answering it. */
  async remove(id) {
    await api.delete(`/unanswered-messages/${id}/`)
  },
}

export default unansweredService
