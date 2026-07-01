import { useEffect, useRef, useState } from 'react'
import { connectSocket, getSocket } from '../services/socketService'

/**
 * Subscribes to realtime events for a single conversation.
 * Returns helpers for typing + sending and live state for incoming
 * messages / typing indicator. Callbacks are kept in refs so the effect
 * doesn't re-subscribe on every render.
 */
export default function useConversationSocket(conversationId, { onMessage } = {}) {
  const [isPeerTyping, setIsPeerTyping] = useState(false)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  useEffect(() => {
    if (!conversationId) return
    const socket = connectSocket()
    socket.emit('conversation:join', conversationId)

    const handleMessage = (payload) => {
      if (payload.conversationId === conversationId) {
        onMessageRef.current?.(payload.message)
      }
    }
    const handleTyping = (payload) => {
      if (payload.conversationId === conversationId) {
        setIsPeerTyping(payload.isTyping)
      }
    }

    socket.on('message:new', handleMessage)
    socket.on('typing', handleTyping)

    return () => {
      socket.emit('conversation:leave', conversationId)
      socket.off('message:new', handleMessage)
      socket.off('typing', handleTyping)
      setIsPeerTyping(false)
    }
  }, [conversationId])

  const emitTyping = (isTyping) => {
    getSocket().emit('typing', { conversationId, isTyping })
  }

  const sendMessage = (body) => {
    getSocket().emit('message:send', { conversationId, body })
  }

  return { isPeerTyping, emitTyping, sendMessage }
}
