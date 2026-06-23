import axiosInstance from './axiosInstance'

/**
 * Workspace / company settings.
 *   GET   /settings/
 *   PATCH /settings/                 (multipart when logo included)
 */
const settingsService = {
  get: async () => {
    const { data } = await axiosInstance.get('/settings/')
    return data
  },

  update: async (payload) => {
    // If a File is present we must send multipart/form-data
    const hasFile = payload.logo instanceof File
    if (hasFile) {
      const form = new FormData()
      Object.entries(payload).forEach(([k, v]) => {
        if (v !== undefined && v !== null) form.append(k, v)
      })
      const { data } = await axiosInstance.patch('/settings/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    }
    const { data } = await axiosInstance.patch('/settings/', payload)
    return data
  },
}

export default settingsService
