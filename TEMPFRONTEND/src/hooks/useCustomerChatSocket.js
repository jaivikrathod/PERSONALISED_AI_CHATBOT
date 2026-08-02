import { useCallback, useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import useWebSocket from './useWebSocket'
import { WS_BASE_URL } from '../utils/constants'
import {
  agentMessageReceived,
  answerReceived,
  chatClosed,
  customerMessageSent,
  fetchSessions,
  messageDelivered,
  socketErrorReceived,
  socketStatusChanged,
} from '../redux/slices/customerChatSlice'

/**
 * Owns the `ws/chat/` connection for the customer widget and translates every
 * server event into a redux action. The wire protocol is unchanged:
 *
 *   out: { message, company_id, customer_user_id, customer_user_name,
 *          customer_user_email, session_id }
 *   in:  { type: "error" | "delivered" | "chat_closed" | "agent_message" }
 *        or an answer payload { answer, session_id, agent_needed, … }
 */
export default function useCustomerChatSocket({
  companyId,
  customerUserId,
  customerUserName,
  customerUserEmail,
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
          break
      }

      dispatch(answerReceived(data))

      // The first message of a conversation creates the session server-side;
      // refresh the list so the new thread appears and stays selected.
      const nextSessionId = data.session_id || activeSessionIdRef.current
      dispatch(
        fetchSessions({
          companyId,
          customerUserId,
          preferredSessionId: nextSessionId ?? undefined,
        }),
      )
    },
    [dispatch, companyId, customerUserId],
  )

  const { status, send } = useWebSocket(`${WS_BASE_URL}/ws/chat/`, {
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
        customer_user_id: customerUserId,
        customer_user_name: customerUserName,
        customer_user_email: customerUserEmail,
        session_id: activeSessionIdRef.current,
      })
      if (sent) dispatch(customerMessageSent(text))
      return sent
    },
    [dispatch, send, companyId, customerUserId, customerUserName, customerUserEmail],
  )

  return { sendMessage }
}
