import { useCallback, useEffect, useRef, useState } from 'react'
import { SOCKET_STATUS } from '../utils/constants'

const RECONNECT_DELAY = 3000

/**
 * Reusable raw-WebSocket connection with JSON encoding and auto-reconnect.
 *
 * Callbacks are held in refs so changing them never tears down the socket —
 * only `url` and `enabled` do. Returns the live status plus a `send` helper
 * that reports whether the frame actually went out (callers use that to fall
 * back to REST).
 */
export default function useWebSocket(url, { enabled = true, onMessage, onOpen } = {}) {
  const [status, setStatus] = useState(SOCKET_STATUS.CONNECTING)

  const socketRef = useRef(null)
  const reconnectRef = useRef(null)
  const onMessageRef = useRef(onMessage)
  const onOpenRef = useRef(onOpen)

  // Keep the latest handlers reachable from the long-lived socket callbacks.
  useEffect(() => {
    onMessageRef.current = onMessage
    onOpenRef.current = onOpen
  })

  useEffect(() => {
    if (!enabled || !url) return undefined

    let disposed = false

    const connect = () => {
      setStatus(SOCKET_STATUS.CONNECTING)

      const socket = new WebSocket(url)
      socketRef.current = socket

      socket.onopen = () => {
        if (disposed) return
        setStatus(SOCKET_STATUS.OPEN)
        onOpenRef.current?.()
      }

      socket.onmessage = (event) => {
        let data
        try {
          data = JSON.parse(event.data)
        } catch {
          return // ignore non-JSON frames
        }
        onMessageRef.current?.(data)
      }

      socket.onerror = () => {
        if (!disposed) setStatus(SOCKET_STATUS.CLOSED)
      }

      socket.onclose = () => {
        if (disposed) return
        setStatus(SOCKET_STATUS.CLOSED)
        // These consoles live in long-lived tabs — keep trying to come back.
        reconnectRef.current = setTimeout(connect, RECONNECT_DELAY)
      }
    }

    connect()

    return () => {
      disposed = true
      clearTimeout(reconnectRef.current)
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [url, enabled])

  /** Sends a JSON payload. Returns false when the socket isn't open. */
  const send = useCallback((payload) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) return false
    socket.send(JSON.stringify(payload))
    return true
  }, [])

  return { status, send, isOpen: status === SOCKET_STATUS.OPEN }
}
