import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import knowledgeBaseService from '../../services/knowledgeBaseService'
import { normalizeError } from '../../services/axiosInstance'
import { DEFAULT_PAGE_SIZE } from '../../utils/constants'

export const fetchFaqs = createAsyncThunk(
  'kb/fetch',
  async (params, { rejectWithValue }) => {
    try {
      return await knowledgeBaseService.list(params)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const createFaq = createAsyncThunk(
  'kb/create',
  async (payload, { rejectWithValue }) => {
    try {
      return await knowledgeBaseService.create(payload)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const updateFaq = createAsyncThunk(
  'kb/update',
  async ({ id, payload }, { rejectWithValue }) => {
    try {
      return await knowledgeBaseService.update(id, payload)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const deleteFaq = createAsyncThunk(
  'kb/delete',
  async (id, { rejectWithValue }) => {
    try {
      return await knowledgeBaseService.remove(id)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const bulkUploadFaqs = createAsyncThunk(
  'kb/bulkUpload',
  async (file, { rejectWithValue }) => {
    try {
      return await knowledgeBaseService.bulkUpload(file)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const fetchEmbeddingStatus = createAsyncThunk(
  'kb/embeddingStatus',
  async (_, { rejectWithValue }) => {
    try {
      return await knowledgeBaseService.embeddingStatus()
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const generateEmbeddings = createAsyncThunk(
  'kb/generateEmbeddings',
  async (opts, { rejectWithValue }) => {
    try {
      return await knowledgeBaseService.generateEmbeddings(opts)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

// Normalize either a paginated DRF response or a plain array.
function normalizeList(payload) {
  if (Array.isArray(payload)) return { items: payload, count: payload.length }
  return { items: payload.results || [], count: payload.count || 0 }
}

const kbSlice = createSlice({
  name: 'kb',
  initialState: {
    items: [],
    count: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    search: '',
    status: 'idle',
    mutating: false,
    error: null,
    embedding: { total: 0, ready: 0, pending: 0, failed: 0 },
    embeddingRunning: false,
  },
  reducers: {
    setKbPage(state, { payload }) {
      state.page = payload
    },
    setKbSearch(state, { payload }) {
      state.search = payload
      state.page = 1
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchFaqs.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchFaqs.fulfilled, (state, { payload }) => {
        const { items, count } = normalizeList(payload)
        state.items = items
        state.count = count
        state.status = 'succeeded'
      })
      .addCase(fetchFaqs.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addCase(createFaq.pending, (state) => {
        state.mutating = true
      })
      .addCase(createFaq.fulfilled, (state, { payload }) => {
        state.mutating = false
        state.items.unshift(payload)
        state.count += 1
      })
      .addCase(createFaq.rejected, (state, { payload }) => {
        state.mutating = false
        state.error = payload
      })
      .addCase(updateFaq.fulfilled, (state, { payload }) => {
        const idx = state.items.findIndex((i) => i.id === payload.id)
        if (idx !== -1) state.items[idx] = payload
      })
      .addCase(deleteFaq.fulfilled, (state, { payload: id }) => {
        state.items = state.items.filter((i) => i.id !== id)
        state.count = Math.max(0, state.count - 1)
      })
      .addCase(fetchEmbeddingStatus.fulfilled, (state, { payload }) => {
        state.embedding = {
          total: payload.total || 0,
          ready: payload.ready || 0,
          pending: payload.pending || 0,
          failed: payload.failed || 0,
        }
      })
      .addCase(generateEmbeddings.pending, (state) => {
        state.embeddingRunning = true
      })
      .addCase(generateEmbeddings.fulfilled, (state) => {
        state.embeddingRunning = false
      })
      .addCase(generateEmbeddings.rejected, (state) => {
        state.embeddingRunning = false
      })
  },
})

export const { setKbPage, setKbSearch } = kbSlice.actions
export default kbSlice.reducer
