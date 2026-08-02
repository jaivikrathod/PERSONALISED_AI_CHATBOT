import { useCallback, useEffect } from 'react'
import { useDispatch } from 'react-redux'
import useWebSocket from './useWebSocket'
import { WS_BASE_URL } from '../utils/constants'
import {
  chatAssigned,
  chatClosedReceived,
  chatMessageReceived,
  chatsReceived,
  historyReceived,
  socketErrorReceived,
  socketStatusChanged,
} from '../redux/slices/agentChatSlice'

/**
 * Owns the `ws/agent/?agent_id=` connection for the agent console.
 *
 *   in:  connected | chats | chat_assigned | history | chat_message |
 *        chat_closed | error
 *   out: { action: "message" | "close" | "history" | "refresh", session_id, … }
 *
 * Sending returns false when the socket is down so the caller can retry the
 * equivalent REST endpoint.
 */
export default function useAgentSocket(agentId, { enabled = true } = {}) {
  const dispatch = useDispatch()

  const handleMessage = useCallback(
    (data) => {
      switch (data.type) {
        case 'connected':
        case 'chats':
          dispatch(chatsReceived(data.chats))
          break
        case 'chat_assigned':
          dispatch(
            chatAssigned({
              chats: data.chats,
              session: data.session || {},
              at: Date.now(),
            }),
          )
          break
        case 'history':
          dispatch(
            historyReceived({
              sessionId: data.session_id,
              messages: data.messages,
            }),
          )
          break
        case 'chat_message':
          dispatch(chatMessageReceived(data.message))
          break
        case 'chat_closed':
          dispatch(chatClosedReceived(data.chats))
          break
        case 'error':
          dispatch(socketErrorReceived(data.error))
          break
        default:
          break
      }
    },
    [dispatch],
  )

  const { status, send } = useWebSocket(
    agentId ? `${WS_BASE_URL}/ws/agent/?agent_id=${agentId}` : null,
    { enabled: enabled && Boolean(agentId), onMessage: handleMessage },
  )

  useEffect(() => {
    dispatch(socketStatusChanged(status))
  }, [dispatch, status])

  const sendMessage = useCallback(
    (sessionId, message) => send({ action: 'message', session_id: sessionId, message }),
    [send],
  )

  const closeChat = useCallback(
    (sessionId) => send({ action: 'close', session_id: sessionId }),
    [send],
  )

  return { sendMessage, closeChat }
}
