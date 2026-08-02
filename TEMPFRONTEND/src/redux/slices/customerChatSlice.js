import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import chatbotService from '../../services/chatbotService'
import { SESSION_STATUS, SOCKET_STATUS } from '../../utils/constants'

/**
 * Customer-facing chatbot widget.
 *
 * Sessions and history come over REST (`/chat/sessions/`, `/chat/history/`);
 * everything live arrives on the `ws/chat/` socket, whose events are applied
 * by the reducers below (see `hooks/useCustomerChatSocket`).
 */

// Optimistic/local bubbles get a string id so they can never collide with the
// numeric primary keys that come back from the server.
let localMessageId = 0
const nextLocalId = () => `local-${++localMessageId}`

const makeMessage = ({ role, text, isError = false, sender = null }) => ({
  id: nextLocalId(),
  role,
  text,
  isError,
  sender,
})

export const fetchSessions = createAsyncThunk(
  'customerChat/fetchSessions',
  async ({ companyId, customerUserId }, { rejectWithValue }) => {
    try {
      return await chatbotService.listSessions({ companyId, customerUserId })
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to load conversations.')
    }
  },
)

export const fetchHistory = createAsyncThunk(
  'customerChat/fetchHistory',
  async ({ sessionId, companyId }, { rejectWithValue }) => {
    try {
      return await chatbotService.getHistory({ sessionId, companyId })
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to load the conversation.')
    }
  },
)

const initialState = {
  sessions: [],
  activeSessionId: null,
  messages: [],
  socketStatus: SOCKET_STATUS.CONNECTING,
  waiting: false,
  loadingSessions: true,
  loadingMessages: false,
  // True once a human agent owns the conversation (the AI stops answering).
  agentHandling: false,
}

const customerChatSlice = createSlice({
  name: 'customerChat',
  initialState,
  reducers: {
    socketStatusChanged(state, { payload }) {
      state.socketStatus = payload
    },

    /** Optimistic bubble for the message the customer just sent. */
    customerMessageSent(state, { payload }) {
      state.messages.push(makeMessage({ role: 'user', text: payload }))
      state.waiting = true
    },

    sessionSelected(state, { payload }) {
      state.activeSessionId = payload
    },

    /** `{ type: "error" }` — surfaced as a red bubble in the thread. */
    socketErrorReceived(state, { payload }) {
      state.waiting = false
      state.messages.push(
        makeMessage({
          role: 'bot',
          text: payload || 'Something went wrong.',
          isError: true,
        }),
      )
    },

    /**
     * `{ type: "delivered" }` — a human owns the chat, so the server only
     * acknowledges delivery; the reply arrives later as `agent_message`.
     */
    messageDelivered(state) {
      state.waiting = false
      state.agentHandling = true
    },

    /** `{ type: "chat_closed" }` */
    chatClosed(state) {
      state.waiting = false
      state.agentHandling = false
      state.messages.push(
        makeMessage({
          role: 'bot',
          text: 'The agent has closed this conversation.',
          sender: 'system',
        }),
      )
    },

    /** `{ type: "agent_message" }` — a live reply from the assigned agent. */
    agentMessageReceived(state, { payload }) {
      state.waiting = false
      state.agentHandling = true
      state.messages.push(
        makeMessage({ role: 'bot', text: payload, sender: 'agent' }),
      )
    },

    /** `{ type: "answer" }` — the AI (or hand-off notice) replying. */
    answerReceived(state, { payload }) {
      state.waiting = false
      if (payload.agent_needed) state.agentHandling = true
      state.messages.push(
        makeMessage({
          role: 'bot',
          text:
            payload.answer || payload.message || 'No matching question found.',
        }),
      )
    },

    resetCustomerChat() {
      return { ...initialState, loadingSessions: false }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchSessions.pending, (state) => {
        state.loadingSessions = true
      })
      .addCase(fetchSessions.fulfilled, (state, { payload, meta }) => {
        state.loadingSessions = false
        state.sessions = payload || []
        // Preserve the current selection; fall back to the freshly created
        // session id (sent down the socket) and then to the newest session.
        state.activeSessionId =
          meta.arg?.preferredSessionId ??
          state.activeSessionId ??
          payload?.[0]?.id ??
          null
      })
      .addCase(fetchSessions.rejected, (state) => {
        state.loadingSessions = false
        state.sessions = []
        state.activeSessionId = null
        state.messages = []
      })
      .addCase(fetchHistory.pending, (state) => {
        state.loadingMessages = true
      })
      .addCase(fetchHistory.fulfilled, (state, { payload, meta }) => {
        state.loadingMessages = false
        // A newer selection won the race — drop this response.
        if (meta.arg.sessionId !== state.activeSessionId) return
        state.messages = (payload.messages || []).map((message) => ({
          id: message.id,
          role: message.role,
          text: message.message,
          isError: false,
          sender: message.sender === 'agent' ? 'agent' : null,
        }))
        state.agentHandling =
          Boolean(payload.agent) && payload.status !== SESSION_STATUS.CLOSED
      })
      .addCase(fetchHistory.rejected, (state) => {
        state.loadingMessages = false
      })
  },
})

export const {
  socketStatusChanged,
  customerMessageSent,
  sessionSelected,
  socketErrorReceived,
  messageDelivered,
  chatClosed,
  agentMessageReceived,
  answerReceived,
  resetCustomerChat,
} = customerChatSlice.actions

export default customerChatSlice.reducer
