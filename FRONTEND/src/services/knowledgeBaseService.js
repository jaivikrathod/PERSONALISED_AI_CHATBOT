import axiosInstance from './axiosInstance'

/**
 * Knowledge Base / FAQ endpoints.
 *   GET    /knowledge-base/?search=&page=&page_size=
 *   POST   /knowledge-base/
 *   PUT    /knowledge-base/:id/
 *   DELETE /knowledge-base/:id/
 *   POST   /knowledge-base/bulk-upload/  (multipart: file)
 */
const knowledgeBaseService = {
  list: async ({ search = '', page = 1, pageSize = 10 } = {}) => {
    const { data } = await axiosInstance.get('/knowledge-base/', {
      params: { search, page, page_size: pageSize },
    })
    return data // expects { results, count } or array
  },

  create: async (payload) => {
    const { data } = await axiosInstance.post('/knowledge-base/', payload)
    return data
  },

  update: async (id, payload) => {
    const { data } = await axiosInstance.put(`/knowledge-base/${id}/`, payload)
    return data
  },

  remove: async (id) => {
    await axiosInstance.delete(`/knowledge-base/${id}/`)
    return id
  },

  bulkUpload: async (file, onUploadProgress) => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await axiosInstance.post(
      '/knowledge-base/bulk-upload/',
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress,
      },
    )
    return data
  },

  // Counts of FAQs by embedding state: { total, ready, pending, failed }.
  embeddingStatus: async () => {
    const { data } = await axiosInstance.get('/knowledge-base/embedding-status/')
    return data
  },

  // Convert FAQs into vector embeddings (all-MiniLM-L6-v2). Synchronous.
  // rebuild=true re-embeds every FAQ; otherwise only pending/failed rows.
  generateEmbeddings: async ({ rebuild = false } = {}) => {
    const { data } = await axiosInstance.post(
      '/knowledge-base/generate-embeddings/',
      { rebuild },
    )
    return data // { success, total, embedded, failed }
  },
}

export default knowledgeBaseService
