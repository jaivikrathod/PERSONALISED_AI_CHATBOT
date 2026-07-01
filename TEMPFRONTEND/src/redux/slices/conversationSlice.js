import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import conversationService from '../../services/conversationService'
import { normalizeError } from '../../services/axiosInstance'

export const fetchConversations = createAsyncThunk(
  'conversations/fetch',
  async (params, { rejectWithValue }) => {
    try {
      const data = await conversationService.list(params)
      return Array.isArray(data) ? { results: data, count: data.length } : data
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const updateConversationStatus = createAsyncThunk(
  'conversations/updateStatus',
  async ({ id, status }, { rejectWithValue }) => {
    try {
      return await conversationService.updateStatus(id, status)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

const conversationSlice = createSlice({
  name: 'conversations',
  initialState: {
    items: [],
    count: 0,
    activeId: null,
    search: '',
    statusFilter: 'all',
    status: 'idle',
    error: null,
  },
  reducers: {
    setActiveConversation(state, { payload }) {
      state.activeId = payload
      // optimistic unread reset
      const conv = state.items.find((c) => c.id === payload)
      if (conv) conv.unread_count = 0
    },
    setConversationSearch(state, { payload }) {
      state.search = payload
    },
    setStatusFilter(state, { payload }) {
      state.statusFilter = payload
    },
    // Called from socket: a brand-new conversation arrived
    conversationReceived(state, { payload }) {
      if (!state.items.find((c) => c.id === payload.id)) {
        state.items.unshift(payload)
        state.count += 1
      }
    },
    // Called from socket/chatSlice: bump preview + unread for a conversation
    conversationBumped(state, { payload }) {
      const { conversationId, lastMessage, incrementUnread } = payload
      const conv = state.items.find((c) => c.id === conversationId)
      if (!conv) return
      conv.last_message = lastMessage
      conv.updated_at = new Date().toISOString()
      if (incrementUnread && conversationId !== state.activeId) {
        conv.unread_count = (conv.unread_count || 0) + 1
      }
      // move to top
      state.items = [conv, ...state.items.filter((c) => c.id !== conversationId)]
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchConversations.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchConversations.fulfilled, (state, { payload }) => {
        state.status = 'succeeded'
        state.items = payload.results || []
        state.count = payload.count || 0
        if (!state.activeId && state.items.length) {
          state.activeId = state.items[0].id
        }
      })
      .addCase(fetchConversations.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addCase(updateConversationStatus.fulfilled, (state, { payload }) => {
        const conv = state.items.find((c) => c.id === payload.id)
        if (conv) conv.status = payload.status
      })
  },
})

export const {
  setActiveConversation,
  setConversationSearch,
  setStatusFilter,
  conversationReceived,
  conversationBumped,
} = conversationSlice.actions
export default conversationSlice.reducer
