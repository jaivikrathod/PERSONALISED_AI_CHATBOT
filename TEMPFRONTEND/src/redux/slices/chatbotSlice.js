import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import chatbotService from '../../services/chatbotService'
import { normalizeError } from '../../services/axiosInstance'

export const fetchChatbots = createAsyncThunk(
  'chatbots/fetch',
  async (_, { rejectWithValue }) => {
    try {      
      const data = await chatbotService.list()
      return Array.isArray(data) ? data : data.results || []
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const createChatbot = createAsyncThunk(
  'chatbots/create',
  async (payload, { rejectWithValue }) => {
    try {
      return await chatbotService.create(payload)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const updateChatbot = createAsyncThunk(
  'chatbots/update',
  async ({ id, payload }, { rejectWithValue }) => {
    try {
      return await chatbotService.update(id, payload)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const deleteChatbot = createAsyncThunk(
  'chatbots/delete',
  async (id, { rejectWithValue }) => {
    try {
      return await chatbotService.remove(id)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

const chatbotSlice = createSlice({
  name: 'chatbots',
  initialState: { items: [], status: 'idle', mutating: false, error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchChatbots.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchChatbots.fulfilled, (state, { payload }) => {
        state.status = 'succeeded'
        state.items = (payload || []).filter(Boolean)
      })
      .addCase(fetchChatbots.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addCase(createChatbot.pending, (state) => {
        state.mutating = true
      })
      .addCase(createChatbot.fulfilled, (state, { payload }) => {
        state.mutating = false
        if (payload) state.items.unshift(payload)
      })
      .addCase(createChatbot.rejected, (state, { payload }) => {
        state.mutating = false
        state.error = payload
      })
      .addCase(updateChatbot.fulfilled, (state, { payload }) => {
        const idx = state.items.findIndex((i) => i.id === payload.id)
        if (idx !== -1) state.items[idx] = payload
      })
      .addCase(deleteChatbot.fulfilled, (state, { payload: id }) => {
        state.items = state.items.filter((i) => i.id !== id)
      })
  },
})

export default chatbotSlice.reducer
