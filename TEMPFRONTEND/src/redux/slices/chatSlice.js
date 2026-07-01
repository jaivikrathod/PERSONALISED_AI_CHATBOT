import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import conversationService from '../../services/conversationService'
import { normalizeError } from '../../services/axiosInstance'

/**
 * Messages for the currently-open conversation, keyed by conversationId so
 * switching threads keeps history cached. Also tracks "load more" cursors.
 */
export const fetchMessages = createAsyncThunk(
  'chat/fetchMessages',
  async ({ conversationId }, { rejectWithValue }) => {
    try {
      const data = await conversationService.getMessages(conversationId)
      const results = Array.isArray(data) ? data : data.results || []
      return { conversationId, messages: results, hasMore: Boolean(data.next) }
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const loadMoreMessages = createAsyncThunk(
  'chat/loadMore',
  async ({ conversationId, before }, { rejectWithValue }) => {
    try {
      const data = await conversationService.getMessages(conversationId, { before })
      const results = Array.isArray(data) ? data : data.results || []
      return { conversationId, messages: results, hasMore: Boolean(data.next) }
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ conversationId, body }, { rejectWithValue }) => {
    try {
      const message = await conversationService.sendMessage(conversationId, body)
      return { conversationId, message }
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    byConversation: {}, // { [id]: { messages, hasMore, loading } }
    sending: false,
    error: null,
  },
  reducers: {
    // Realtime inbound message from socket
    messageReceived(state, { payload }) {
      const { conversationId, message } = payload
      const bucket = (state.byConversation[conversationId] ??= {
        messages: [],
        hasMore: false,
        loading: false,
      })
      if (!bucket.messages.some((m) => m.id === message.id)) {
        bucket.messages.push(message)
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMessages.pending, (state, { meta }) => {
        const id = meta.arg.conversationId
        state.byConversation[id] = {
          messages: state.byConversation[id]?.messages || [],
          hasMore: false,
          loading: true,
        }
      })
      .addCase(fetchMessages.fulfilled, (state, { payload }) => {
        state.byConversation[payload.conversationId] = {
          messages: payload.messages,
          hasMore: payload.hasMore,
          loading: false,
        }
      })
      .addCase(loadMoreMessages.fulfilled, (state, { payload }) => {
        const bucket = state.byConversation[payload.conversationId]
        if (bucket) {
          bucket.messages = [...payload.messages, ...bucket.messages]
          bucket.hasMore = payload.hasMore
        }
      })
      .addCase(sendMessage.pending, (state) => {
        state.sending = true
      })
      .addCase(sendMessage.fulfilled, (state, { payload }) => {
        state.sending = false
        const bucket = (state.byConversation[payload.conversationId] ??= {
          messages: [],
          hasMore: false,
          loading: false,
        })
        if (!bucket.messages.some((m) => m.id === payload.message.id)) {
          bucket.messages.push(payload.message)
        }
      })
      .addCase(sendMessage.rejected, (state, { payload }) => {
        state.sending = false
        state.error = payload
      })
  },
})

export const { messageReceived } = chatSlice.actions
export default chatSlice.reducer
