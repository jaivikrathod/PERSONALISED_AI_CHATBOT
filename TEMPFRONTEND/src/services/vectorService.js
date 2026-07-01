import api from './axiosInstance'

/** Vectorization API calls. */
export const vectorService = {
  /**
   * Trigger vectorization for every un-vectorized question of a company.
   * Returns the backend summary, e.g.
   *   { message, total_questions, processed_questions, failed_questions }
   * or { message: "All questions are already vectorized." }
   */
  async vectorizeCompany(companyId) {
    const { data } = await api.post(`/vectorize/${companyId}/`)
    return data
  },
}

export default vectorService
