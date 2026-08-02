import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import unansweredService from '../../services/unansweredService'

/**
 * Inbox of customer messages the chatbot could not answer
 * (`questions.UnansweredMessageViewSet`). Answering one creates a Question,
 * vectorizes it immediately and removes the inbox row.
 */

export const fetchUnanswered = createAsyncThunk(
  'unanswered/fetch',
  async (companyId, { rejectWithValue }) => {
    try {
      return await unansweredService.list(companyId)
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to load unanswered messages.')
    }
  },
)

export const resolveUnanswered = createAsyncThunk(
  'unanswered/resolve',
  async ({ id, answer }, { rejectWithValue }) => {
    try {
      const question = await unansweredService.resolve(id, answer)
      return { id, question }
    } catch (err) {
      // The backend returns { error: "…" } for an empty answer / failed
      // embedding; axiosInstance already flattens that into `message`.
      return rejectWithValue(err.message || 'Failed to save the answer.')
    }
  },
)

export const dismissUnanswered = createAsyncThunk(
  'unanswered/dismiss',
  async (id, { rejectWithValue }) => {
    try {
      return await unansweredService.remove(id)
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to delete message.')
    }
  },
)

const unansweredSlice = createSlice({
  name: 'unanswered',
  initialState: {
    items: [],
    status: 'idle', // idle | loading | succeeded | failed
    resolvingId: null,
    error: null,
  },
  reducers: {
    clearUnansweredError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchUnanswered.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchUnanswered.fulfilled, (state, { payload }) => {
        state.status = 'succeeded'
        state.items = Array.isArray(payload) ? payload : payload?.results || []
      })
      .addCase(fetchUnanswered.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addCase(resolveUnanswered.pending, (state, { meta }) => {
        state.resolvingId = meta.arg.id
        state.error = null
      })
      .addCase(resolveUnanswered.fulfilled, (state, { payload }) => {
        state.resolvingId = null
        state.items = state.items.filter((item) => item.id !== payload.id)
      })
      .addCase(resolveUnanswered.rejected, (state, { payload }) => {
        state.resolvingId = null
        state.error = payload
      })
      .addCase(dismissUnanswered.fulfilled, (state, { payload: id }) => {
        state.items = state.items.filter((item) => item.id !== id)
      })
      .addCase(dismissUnanswered.rejected, (state, { payload }) => {
        state.error = payload
      })
  },
})

export const { clearUnansweredError } = unansweredSlice.actions
export default unansweredSlice.reducer
