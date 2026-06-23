import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import analyticsService from '../../services/analyticsService'
import { normalizeError } from '../../services/axiosInstance'

export const fetchOverview = createAsyncThunk(
  'analytics/overview',
  async (range, { rejectWithValue }) => {
    try {
      return await analyticsService.overview(range)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const fetchConversationsSeries = createAsyncThunk(
  'analytics/series',
  async (params, { rejectWithValue }) => {
    try {
      return await analyticsService.conversationsSeries(params)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const fetchTopFaqs = createAsyncThunk(
  'analytics/topFaqs',
  async (_, { rejectWithValue }) => {
    try {
      return await analyticsService.topFaqs()
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const fetchUnanswered = createAsyncThunk(
  'analytics/unanswered',
  async (params, { rejectWithValue }) => {
    try {
      const data = await analyticsService.unanswered(params)
      return Array.isArray(data) ? { results: data, count: data.length } : data
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const convertUnanswered = createAsyncThunk(
  'analytics/convert',
  async ({ id, payload }, { rejectWithValue }) => {
    try {
      await analyticsService.convertUnanswered(id, payload)
      return id
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState: {
    overview: null,
    series: [],
    weeklySeries: [],
    topFaqs: [],
    unanswered: [],
    unansweredCount: 0,
    status: 'idle',
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchOverview.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchOverview.fulfilled, (state, { payload }) => {
        state.status = 'succeeded'
        state.overview = payload
      })
      .addCase(fetchOverview.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addCase(fetchConversationsSeries.fulfilled, (state, { payload, meta }) => {
        const data = Array.isArray(payload) ? payload : payload.results || []
        if (meta.arg?.granularity === 'week') state.weeklySeries = data
        else state.series = data
      })
      .addCase(fetchTopFaqs.fulfilled, (state, { payload }) => {
        state.topFaqs = Array.isArray(payload) ? payload : payload.results || []
      })
      .addCase(fetchUnanswered.fulfilled, (state, { payload }) => {
        state.unanswered = payload.results || []
        state.unansweredCount = payload.count || 0
      })
      .addCase(convertUnanswered.fulfilled, (state, { payload: id }) => {
        state.unanswered = state.unanswered.filter((u) => u.id !== id)
        state.unansweredCount = Math.max(0, state.unansweredCount - 1)
      })
  },
})

export default analyticsSlice.reducer
