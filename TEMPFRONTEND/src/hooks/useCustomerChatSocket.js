import { useCallback, useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import useWebSocket from './useWebSocket'
import { WS_BASE_URL } from '../utils/constants'
import {
  agentMessageReceived,
  answerReceived,
  chatClosed,
  customerMessageSent,
  messageDelivered,
  sessionEstablished,
  socketErrorReceived,
  socketStatusChanged,
} from '../redux/slices/customerChatSlice'

/**
 * Owns the `ws/chat/` connection for the public widget and translates every
 * server event into a redux action. The wire protocol is unchanged:
 *
 *   out: { message, company_id, customer_user_id, customer_user_name,
 *          customer_user_email, session_id }
 *   in:  { type: "error" | "delivered" | "chat_closed" | "agent_message" }
 *        or an answer payload { answer, session_id, agent_needed, … }
 *
 * `customer_user_*` are optional — anonymous visitors send whatever the
 * pre-chat form collected (possibly nothing at all).
 */
export default function useCustomerChatSocket({
  companyId,
  customerUserId = null,
  customerUserName = '',
  customerUserEmail = '',
}) {
  const dispatch = useDispatch()
  const activeSessionId = useSelector((s) => s.customerChat.activeSessionId)

  // The socket handler is created once, so it reads the live selection from a
  // ref instead of closing over a stale value.
  const activeSessionIdRef = useRef(activeSessionId)
  useEffect(() => {
    activeSessionIdRef.current = activeSessionId
  }, [activeSessionId])

  const handleMessage = useCallback(
    (data) => {
      // Every server frame that knows the session carries it; the first message
      // of a conversation is what creates it server-side. `session_token` comes
      // with it so a later reload can prove this browser owns the chat.
      if (data.session_id) {
        dispatch(
          sessionEstablished({
            sessionId: data.session_id,
            token: data.session_token,
          }),
        )
      }

      switch (data.type) {
        case 'error':
          dispatch(socketErrorReceived(data.error))
          return
        case 'delivered':
          dispatch(messageDelivered())
          return
        case 'chat_closed':
          dispatch(chatClosed())
          return
        case 'agent_message':
          dispatch(agentMessageReceived(data.answer))
          return
        default:
          dispatch(answerReceived(data))
      }
    },
    [dispatch],
  )

  const { status, send } = useWebSocket(`${WS_BASE_URL}/ws/chat/`, {
    enabled: Boolean(companyId),
    onMessage: handleMessage,
  })

  useEffect(() => {
    dispatch(socketStatusChanged(status))
  }, [dispatch, status])

  /** Optimistically renders the bubble, then pushes it down the socket. */
  const sendMessage = useCallback(
    (text) => {
      const sent = send({
        message: text,
        company_id: companyId,
        customer_user_id: customerUserId || null,
        customer_user_name: customerUserName || '',
        customer_user_email: customerUserEmail || '',
        session_id: activeSessionIdRef.current,
      })
      if (sent) dispatch(customerMessageSent(text))
      return sent
    },
    [dispatch, send, companyId, customerUserId, customerUserName, customerUserEmail],
  )

  return { sendMessage }
}
