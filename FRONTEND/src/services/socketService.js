import { io } from 'socket.io-client'
import { WS_URL } from '../utils/constants'
import { tokenStore } from '../utils/storage'

/**
 * Singleton Socket.io client for realtime conversations & agent presence.
 * Server events expected (rename to match your backend):
 *   'message:new'      { conversationId, message }
 *   'conversation:new' { conversation }
 *   'typing'           { conversationId, user, isTyping }
 *   'presence'         { userId, status }
 * Client emits:
 *   'conversation:join'  conversationId
 *   'conversation:leave' conversationId
 *   'typing'             { conversationId, isTyping }
 *   'message:send'       { conversationId, body }
 */
let socket = null

export function getSocket() {
  if (socket) return socket
  socket = io(WS_URL, {
    autoConnect: false,
    transports: ['websocket'],
    auth: { token: tokenStore.getAccess() },
  })
  return socket
}

export function connectSocket() {
  const s = getSocket()
  if (!s.connected) {
    s.auth = { token: tokenStore.getAccess() }
    s.connect()
  }
  return s
}

export function disconnectSocket() {
  if (socket?.connected) socket.disconnect()
}
