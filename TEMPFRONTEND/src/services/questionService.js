import api from './axiosInstance'

/** CRUD calls for the Question resource. */
export const questionService = {
  /** List questions for a company. */
  async list(companyId) {
    const { data } = await api.get('/questions/', {
      params: { company_id: companyId },
    })
    return data
  },

  /** Create a question/answer pair for a company. */
  async create({ companyId, question, answer }) {
    const { data } = await api.post('/questions/', {
      company: companyId,
      question,
      answer,
    })
    return data
  },

  /** Soft-delete a question. */
  async remove(id) {
    await api.delete(`/questions/${id}/`)
  },
}

export default questionService
