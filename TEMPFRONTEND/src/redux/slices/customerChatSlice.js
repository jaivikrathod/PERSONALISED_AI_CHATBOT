import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import chatbotService from '../../services/chatbotService'
import { SESSION_STATUS, SOCKET_STATUS } from '../../utils/constants'

/**
 * Public chatbot widget (`/chat/:companyId`).
 *
 * Visitors are anonymous, so there is no inbox to list: a browser holds a
 * single conversation per company, replayed over REST (`/chat/history/`) and
 * kept live on the `ws/chat/` socket, whose events are applied by the reducers
 * below (see `hooks/useCustomerChatSocket`).
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
  activeSessionId: null,
  messages: [],
  socketStatus: SOCKET_STATUS.CONNECTING,
  waiting: false,
  loadingMessages: false,
  // True once a human agent owns the conversation (the AI stops answering).
  agentHandling: false,
  // True after the agent closes the chat; the next message opens a new session.
  closed: false,
}

const customerChatSlice = createSlice({
  name: 'customerChat',
  initialState,
  reducers: {
    socketStatusChanged(state, { payload }) {
      state.socketStatus = payload
    },

    /** Optimistic bubble for the message the visitor just sent. */
    customerMessageSent(state, { payload }) {
      state.messages.push(makeMessage({ role: 'user', text: payload }))
      state.waiting = true
      state.closed = false
    },

    /**
     * The server told us which session this conversation belongs to — either
     * the one we resumed from localStorage or a freshly created one.
     */
    sessionEstablished(state, { payload }) {
      if (payload && payload !== state.activeSessionId) {
        state.activeSessionId = payload
      }
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

    /**
     * `{ type: "chat_closed" }` — the session is finished server-side. Drop the
     * selection so the visitor's next message starts a fresh conversation
     * instead of reopening a closed one.
     */
    chatClosed(state) {
      state.waiting = false
      state.agentHandling = false
      state.activeSessionId = null
      state.closed = true
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

    /** "Start a new chat" — forgets the current thread entirely. */
    startNewChat() {
      return initialState
    },

    resetCustomerChat() {
      return initialState
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchHistory.pending, (state) => {
        state.loadingMessages = true
      })
      .addCase(fetchHistory.fulfilled, (state, { payload, meta }) => {
        state.loadingMessages = false
        // A newer session won the race — drop this response.
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
        state.closed = payload.status === SESSION_STATUS.CLOSED
      })
      .addCase(fetchHistory.rejected, (state) => {
        // The stored session id no longer resolves (deleted, wrong company):
        // fall back to a clean slate rather than an empty broken thread.
        state.loadingMessages = false
        state.activeSessionId = null
        state.messages = []
      })
  },
})

export const {
  socketStatusChanged,
  customerMessageSent,
  sessionEstablished,
  socketErrorReceived,
  messageDelivered,
  chatClosed,
  agentMessageReceived,
  answerReceived,
  startNewChat,
  resetCustomerChat,
} = customerChatSlice.actions

export default customerChatSlice.reducer
