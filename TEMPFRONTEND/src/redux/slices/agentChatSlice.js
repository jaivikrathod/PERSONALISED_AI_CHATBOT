import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import agentService from '../../services/agentService'
import { SESSION_STATUS, SOCKET_STATUS } from '../../utils/constants'

/**
 * Human-agent console.
 *
 * The inbox and history load over REST so the console renders even when the
 * socket is down; `ws/agent/?token=` then drives everything live (see
 * `hooks/useAgentSocket`). Sending falls back to REST when the socket dropped.
 */

/** History (REST serializer) and live socket events use different shapes. */
export function normalizeMessage(raw) {
  return {
    id: raw.id,
    sessionId: raw.session_id ?? raw.session,
    text: raw.message,
    sender: raw.sender || (raw.is_ai ? 'ai' : raw.sent_by_us ? 'agent' : 'customer'),
    customerName: raw.customer_user_name || '',
    createdAt: raw.created_at,
  }
}

export const fetchAgentChats = createAsyncThunk(
  'agentChat/fetchChats',
  async (_, { rejectWithValue }) => {
    try {
      return await agentService.listChats()
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to load chats.')
    }
  },
)

export const fetchAgentHistory = createAsyncThunk(
  'agentChat/fetchHistory',
  async ({ sessionId }, { rejectWithValue }) => {
    try {
      return await agentService.getHistory({ sessionId })
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to load the conversation.')
    }
  },
)

/** REST fallback used only when the socket is not open. */
export const sendAgentMessage = createAsyncThunk(
  'agentChat/sendMessage',
  async ({ sessionId, message }, { rejectWithValue }) => {
    try {
      return await agentService.sendMessage({ sessionId, message })
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to send the message.')
    }
  },
)

/** REST fallback used only when the socket is not open. */
export const closeAgentChat = createAsyncThunk(
  'agentChat/closeChat',
  async ({ sessionId }, { rejectWithValue }) => {
    try {
      await agentService.closeChat({ sessionId })
      return sessionId
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to close the chat.')
    }
  },
)

const agentChatSlice = createSlice({
  name: 'agentChat',
  initialState: {
    chats: [],
    activeSessionId: null,
    messages: [],
    unread: {}, // { [sessionId]: true }
    alert: null, // { sessionId, at } — newly assigned chat banner
    socketStatus: SOCKET_STATUS.CONNECTING,
    loadingChats: true,
    loadingMessages: false,
    error: '',
  },
  reducers: {
    socketStatusChanged(state, { payload }) {
      state.socketStatus = payload
    },

    /** `{ type: "connected" | "chats" }` */
    chatsReceived(state, { payload }) {
      state.chats = payload || []
      state.loadingChats = false
    },

    /** `{ type: "chat_assigned" }` */
    chatAssigned(state, { payload }) {
      const { chats, session, at } = payload
      state.chats = chats || []
      state.loadingChats = false
      state.alert = { sessionId: session?.id, at }
      if (session?.id != null) state.unread[session.id] = true
    },

    /** `{ type: "history" }` — pushed when the agent asks over the socket. */
    historyReceived(state, { payload }) {
      if (payload.sessionId !== state.activeSessionId) return
      state.messages = (payload.messages || []).map(normalizeMessage)
      state.loadingMessages = false
    },

    /** `{ type: "chat_message" }` */
    chatMessageReceived(state, { payload }) {
      const message = normalizeMessage(payload)

      if (message.sessionId === state.activeSessionId) {
        if (!state.messages.some((item) => item.id === message.id)) {
          state.messages.push(message)
        }
      } else if (message.sender === 'customer') {
        state.unread[message.sessionId] = true
      }

      // Keep the sidebar preview / ordering in sync.
      const chat = state.chats.find((item) => item.id === message.sessionId)
      if (chat) {
        chat.last_message = message.text
        chat.last_message_at = message.createdAt
      }
    },

    /** `{ type: "chat_closed" }` */
    chatClosedReceived(state, { payload }) {
      state.chats = payload || []
    },

    socketErrorReceived(state, { payload }) {
      state.error = payload || 'Something went wrong.'
    },

    /** Opening a conversation resets the thread and clears its unread flag. */
    chatOpened(state, { payload: sessionId }) {
      state.activeSessionId = sessionId
      delete state.unread[sessionId]
      if (state.alert?.sessionId === sessionId) state.alert = null
      state.messages = []
      state.loadingMessages = true
      state.error = ''
    },

    alertDismissed(state) {
      state.alert = null
    },

    clearAgentError(state) {
      state.error = ''
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAgentChats.fulfilled, (state, { payload }) => {
        state.loadingChats = false
        state.chats = payload || []
      })
      .addCase(fetchAgentChats.rejected, (state, { payload }) => {
        state.loadingChats = false
        state.error = payload
      })
      .addCase(fetchAgentHistory.fulfilled, (state, { payload, meta }) => {
        state.loadingMessages = false
        // A newer selection won the race — drop this response.
        if (meta.arg.sessionId !== state.activeSessionId) return
        state.messages = (payload.messages || []).map(normalizeMessage)
      })
      .addCase(fetchAgentHistory.rejected, (state, { payload }) => {
        state.loadingMessages = false
        state.error = payload
      })
      .addCase(sendAgentMessage.fulfilled, (state, { payload }) => {
        const message = normalizeMessage(payload)
        if (!state.messages.some((item) => item.id === message.id)) {
          state.messages.push(message)
        }
      })
      .addCase(sendAgentMessage.rejected, (state, { payload }) => {
        state.error = payload
      })
      .addCase(closeAgentChat.fulfilled, (state, { payload: sessionId }) => {
        const chat = state.chats.find((item) => item.id === sessionId)
        if (chat) chat.status = SESSION_STATUS.CLOSED
      })
      .addCase(closeAgentChat.rejected, (state, { payload }) => {
        state.error = payload
      })
  },
})

// ---- selectors ---------------------------------------------------------
export const selectActiveChat = (state) =>
  state.agentChat.chats.find((chat) => chat.id === state.agentChat.activeSessionId) ||
  null

export const selectOpenChatCount = (state) =>
  state.agentChat.chats.filter((chat) => chat.status !== SESSION_STATUS.CLOSED).length

export const {
  socketStatusChanged,
  chatsReceived,
  chatAssigned,
  historyReceived,
  chatMessageReceived,
  chatClosedReceived,
  socketErrorReceived,
  chatOpened,
  alertDismissed,
  clearAgentError,
} = agentChatSlice.actions

export default agentChatSlice.reducer
