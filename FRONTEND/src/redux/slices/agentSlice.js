import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import agentService from '../../services/agentService'
import { normalizeError } from '../../services/axiosInstance'

export const fetchAgents = createAsyncThunk(
  'agents/fetch',
  async (_, { rejectWithValue }) => {
    try {
      const data = await agentService.listAgents()
      return Array.isArray(data) ? data : data.results || []
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const takeOverConversation = createAsyncThunk(
  'agents/takeOver',
  async (conversationId, { rejectWithValue }) => {
    try {
      return await agentService.takeOver(conversationId)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const assignConversation = createAsyncThunk(
  'agents/assign',
  async ({ conversationId, agentId }, { rejectWithValue }) => {
    try {
      return await agentService.assign(conversationId, agentId)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const transferConversation = createAsyncThunk(
  'agents/transfer',
  async ({ conversationId, agentId }, { rejectWithValue }) => {
    try {
      return await agentService.transfer(conversationId, agentId)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const resolveConversation = createAsyncThunk(
  'agents/resolve',
  async (conversationId, { rejectWithValue }) => {
    try {
      return await agentService.resolve(conversationId)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

const agentSlice = createSlice({
  name: 'agents',
  initialState: { items: [], status: 'idle', acting: false, error: null },
  reducers: {
    // socket 'presence' event
    presenceUpdated(state, { payload }) {
      const agent = state.items.find((a) => a.id === payload.userId)
      if (agent) agent.status = payload.status
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAgents.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchAgents.fulfilled, (state, { payload }) => {
        state.status = 'succeeded'
        state.items = payload
      })
      .addCase(fetchAgents.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addMatcher(
        (action) =>
          action.type.startsWith('agents/') && action.type.endsWith('/pending'),
        (state) => {
          state.acting = true
        },
      )
      .addMatcher(
        (action) =>
          action.type.startsWith('agents/') &&
          (action.type.endsWith('/fulfilled') ||
            action.type.endsWith('/rejected')),
        (state) => {
          state.acting = false
        },
      )
  },
})

export const { presenceUpdated } = agentSlice.actions
export default agentSlice.reducer
