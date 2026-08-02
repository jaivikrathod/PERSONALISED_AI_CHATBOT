import api from './axiosInstance'

/** CRUD calls for the Question resource (`questions.QuestionViewSet`). */
export const questionService = {
  /**
   * List questions for a company. `search` maps to DRF's SearchFilter
   * (`search_fields = ["question"]`) and is omitted when empty so the request
   * stays identical to the unfiltered call.
   */
  async list(companyId, { search } = {}) {
    const { data } = await api.get('/questions/', {
      params: {
        company_id: companyId,
        ...(search ? { search } : {}),
      },
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

  /** Soft-delete a question (the backend archives it and clears its vector). */
  async remove(id) {
    await api.delete(`/questions/${id}/`)
    return id
  },
}

export default questionService
