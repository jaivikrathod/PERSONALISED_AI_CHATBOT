import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import agentService from '../services/agentService'
import { USER_TYPES, WS_BASE_URL } from '../utils/constants'

/** History (REST serializer) and live events use slightly different shapes. */
function normalizeMessage(raw) {
  return {
    id: raw.id,
    sessionId: raw.session_id ?? raw.session,
    text: raw.message,
    sender: raw.sender || (raw.is_ai ? 'ai' : raw.sent_by_us ? 'agent' : 'customer'),
    customerName: raw.customer_user_name || '',
    createdAt: raw.created_at,
  }
}

const SENDER_STYLES = {
  customer: 'rounded-bl-sm bg-white text-gray-800 shadow-sm dark:bg-gray-800 dark:text-gray-100',
  ai: 'rounded-br-sm bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200',
  agent: 'rounded-br-sm bg-brand-600 text-white',
}

const SENDER_LABELS = {
  customer: 'Customer',
  ai: 'AI',
  agent: 'You',
}

const STATUS_LABELS = {
  connecting: { text: 'Connecting…', tone: 'bg-amber-400' },
  open: { text: 'Live', tone: 'bg-emerald-500' },
  closed: { text: 'Disconnected', tone: 'bg-red-500' },
}

export default function AgentPage() {
  const { user, logout } = useAuth()
  const agentId = user?.id
  const isAgent = user?.type === USER_TYPES.AGENT

  const [status, setStatus] = useState('connecting')
  const [chats, setChats] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [loadingChats, setLoadingChats] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [unread, setUnread] = useState({}) // { [sessionId]: true }
  const [alert, setAlert] = useState(null) // newly assigned chat banner
  const [input, setInput] = useState('')
  const [error, setError] = useState('')

  const socketRef = useRef(null)
  const activeSessionIdRef = useRef(null)
  const scrollRef = useRef(null)
  const reconnectRef = useRef(null)

  // Mirrored into a ref so the long-lived socket handler can read the current
  // selection without being re-created on every switch.
  useEffect(() => {
    activeSessionIdRef.current = activeSessionId
  }, [activeSessionId])

  const activeChat = useMemo(
    () => chats.find((chat) => chat.id === activeSessionId) || null,
    [chats, activeSessionId],
  )
  const isClosed = activeChat?.status === 'closed'
  const waitingCount = chats.filter((chat) => chat.status !== 'closed').length

  // --- Socket -------------------------------------------------------------
  const handleEvent = useCallback((data) => {
    switch (data.type) {
      case 'connected':
      case 'chats':
        setChats(data.chats || [])
        setLoadingChats(false)
        break

      case 'chat_assigned': {
        setChats(data.chats || [])
        const session = data.session || {}
        setAlert({ sessionId: session.id, at: Date.now() })
        setUnread((prev) => ({ ...prev, [session.id]: true }))
        break
      }

      case 'history':
        if (data.session_id === activeSessionIdRef.current) {
          setMessages((data.messages || []).map(normalizeMessage))
          setLoadingMessages(false)
        }
        break

      case 'chat_message': {
        const message = normalizeMessage(data.message)
        if (message.sessionId === activeSessionIdRef.current) {
          setMessages((prev) =>
            prev.some((item) => item.id === message.id) ? prev : [...prev, message],
          )
        } else if (message.sender === 'customer') {
          setUnread((prev) => ({ ...prev, [message.sessionId]: true }))
        }
        // Keep the sidebar preview / ordering in sync.
        setChats((prev) =>
          prev.map((chat) =>
            chat.id === message.sessionId
              ? { ...chat, last_message: message.text, last_message_at: message.createdAt }
              : chat,
          ),
        )
        break
      }

      case 'chat_closed':
        setChats(data.chats || [])
        break

      case 'error':
        setError(data.error || 'Something went wrong.')
        break

      default:
        break
    }
  }, [])

  useEffect(() => {
    if (!agentId || !isAgent) return undefined

    let disposed = false

    const connect = () => {
      const socket = new WebSocket(`${WS_BASE_URL}/ws/agent/?agent_id=${agentId}`)
      socketRef.current = socket

      socket.onopen = () => setStatus('open')
      socket.onmessage = (event) => {
        let data
        try {
          data = JSON.parse(event.data)
        } catch {
          return
        }
        handleEvent(data)
      }
      socket.onerror = () => setStatus('closed')
      socket.onclose = () => {
        setStatus('closed')
        if (!disposed) {
          // Console is a long-lived tab — keep trying to come back.
          reconnectRef.current = setTimeout(connect, 3000)
        }
      }
    }

    // REST first so the inbox renders even if the socket is unavailable.
    agentService
      .listChats(agentId)
      .then((data) => {
        if (!disposed) setChats(data)
      })
      .catch((err) => !disposed && setError(err.message || 'Failed to load chats.'))
      .finally(() => !disposed && setLoadingChats(false))

    connect()

    return () => {
      disposed = true
      clearTimeout(reconnectRef.current)
      socketRef.current?.close()
    }
  }, [agentId, isAgent, handleEvent])

  // --- Open a conversation -------------------------------------------------
  const openChat = async (sessionId) => {
    setActiveSessionId(sessionId)
    activeSessionIdRef.current = sessionId
    setUnread((prev) => {
      const next = { ...prev }
      delete next[sessionId]
      return next
    })
    setAlert((prev) => (prev?.sessionId === sessionId ? null : prev))
    setMessages([])
    setLoadingMessages(true)
    setError('')

    try {
      const data = await agentService.getHistory({ agentId, sessionId })
      if (activeSessionIdRef.current !== sessionId) return
      setMessages((data.messages || []).map(normalizeMessage))
    } catch (err) {
      setError(err.message || 'Failed to load the conversation.')
    } finally {
      setLoadingMessages(false)
    }
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loadingMessages])

  // --- Reply ---------------------------------------------------------------
  const handleSend = async (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || !activeSessionId || isClosed) return

    setInput('')
    setError('')

    const socket = socketRef.current
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({ action: 'message', session_id: activeSessionId, message: text }),
      )
      return
    }

    // Socket down: post over REST, then show it locally.
    try {
      const saved = await agentService.sendMessage({
        agentId,
        sessionId: activeSessionId,
        message: text,
      })
      setMessages((prev) => [...prev, normalizeMessage(saved)])
    } catch (err) {
      setError(err.message || 'Failed to send the message.')
    }
  }

  const handleClose = async () => {
    if (!activeSessionId) return
    const socket = socketRef.current
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: 'close', session_id: activeSessionId }))
      return
    }
    try {
      await agentService.closeChat({ agentId, sessionId: activeSessionId })
      setChats((prev) =>
        prev.map((chat) =>
          chat.id === activeSessionId ? { ...chat, status: 'closed' } : chat,
        ),
      )
    } catch (err) {
      setError(err.message || 'Failed to close the chat.')
    }
  }

  if (!isAgent) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100 p-6 text-center dark:bg-gray-950">
        <div className="max-w-sm rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Agent console
          </h1>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            This page is only available to users of type Agent.
          </p>
          <Button className="mt-4" variant="secondary" onClick={logout}>
            Log out
          </Button>
        </div>
      </div>
    )
  }

  const statusLabel = STATUS_LABELS[status]

  return (
    <div className="flex h-screen bg-gray-100 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <aside className="flex w-80 flex-col border-r border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
        <div className="border-b border-gray-200 px-4 py-4 dark:border-gray-800">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h1 className="text-lg font-semibold">Agent console</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">{user?.name}</p>
              <div className="mt-1 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <span className={`inline-block h-2 w-2 rounded-full ${statusLabel.tone}`} />
                {statusLabel.text}
              </div>
            </div>
            <Button variant="secondary" onClick={logout}>
              Log out
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <div className="mb-3 flex items-center justify-between px-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Assigned chats ({waitingCount})
            </span>
            {loadingChats && <Spinner className="h-4 w-4 text-gray-400" />}
          </div>

          <div className="space-y-2">
            {chats.map((chat) => {
              const isActive = chat.id === activeSessionId
              const hasUnread = Boolean(unread[chat.id])
              return (
                <button
                  key={chat.id}
                  type="button"
                  onClick={() => openChat(chat.id)}
                  className={
                    'w-full rounded-xl border px-3 py-3 text-left transition ' +
                    (isActive
                      ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/10'
                      : 'border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-800 dark:bg-gray-900 dark:hover:bg-gray-800')
                  }
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 truncate text-sm font-medium">
                      {hasUnread && (
                        <span className="h-2 w-2 shrink-0 rounded-full bg-brand-600" />
                      )}
                      Chat #{chat.id}
                    </div>
                    <span
                      className={
                        'shrink-0 rounded-full px-2 py-0.5 text-[11px] ' +
                        (chat.status === 'closed'
                          ? 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                          : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400')
                      }
                    >
                      {chat.status}
                    </span>
                  </div>
                  <div className="mt-1 truncate text-xs text-gray-500 dark:text-gray-400">
                    {chat.last_message || 'No messages yet.'}
                  </div>
                </button>
              )
            })}

            {!loadingChats && chats.length === 0 && (
              <div className="rounded-xl border border-dashed border-gray-300 px-3 py-6 text-center text-sm text-gray-400 dark:border-gray-700">
                No chats assigned yet. You&apos;ll be notified the moment one
                arrives.
              </div>
            )}
          </div>
        </div>
      </aside>

      <main className="flex flex-1 flex-col">
        {alert && (
          <div className="flex items-center justify-between gap-3 border-b border-brand-200 bg-brand-50 px-5 py-3 text-sm dark:border-brand-500/30 dark:bg-brand-500/10">
            <span className="font-medium text-brand-700 dark:text-brand-300">
              New chat assigned to you — Chat #{alert.sessionId}
            </span>
            <div className="flex items-center gap-2">
              <Button onClick={() => openChat(alert.sessionId)}>Take chat</Button>
              <Button variant="secondary" onClick={() => setAlert(null)}>
                Dismiss
              </Button>
            </div>
          </div>
        )}

        <div className="border-b border-gray-200 bg-white px-5 py-4 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">
                {activeChat ? `Chat #${activeChat.id}` : 'No conversation selected'}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {activeChat
                  ? isClosed
                    ? 'This conversation is closed.'
                    : 'You are answering this customer — the AI is paused.'
                  : 'Pick a chat from the list to start answering.'}
              </p>
            </div>
            {activeChat && !isClosed && (
              <Button variant="secondary" onClick={handleClose}>
                Close chat
              </Button>
            )}
          </div>
        </div>

        {error && (
          <div className="border-b border-red-200 bg-red-50 px-5 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        )}

        <div
          ref={scrollRef}
          className="flex-1 space-y-3 overflow-y-auto bg-gray-50 p-4 dark:bg-gray-950"
        >
          {loadingMessages && (
            <div className="flex h-full items-center justify-center text-sm text-gray-400">
              Loading conversation…
            </div>
          )}

          {!loadingMessages && !activeChat && (
            <div className="flex h-full items-center justify-center text-center text-sm text-gray-400">
              When the bot cannot answer a question, the chat is assigned to a free
              agent and shows up here instantly.
            </div>
          )}

          {!loadingMessages &&
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender === 'customer' ? 'justify-start' : 'justify-end'}`}
              >
                <div className="max-w-[80%]">
                  <div
                    className={
                      'mb-1 text-[11px] text-gray-400 ' +
                      (message.sender === 'customer' ? 'text-left' : 'text-right')
                    }
                  >
                    {message.sender === 'customer' && message.customerName
                      ? message.customerName
                      : SENDER_LABELS[message.sender]}
                  </div>
                  <div
                    className={
                      'whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ' +
                      SENDER_STYLES[message.sender]
                    }
                  >
                    {message.text}
                  </div>
                </div>
              </div>
            ))}
        </div>

        <form
          onSubmit={handleSend}
          className="border-t border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
        >
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                !activeChat
                  ? 'Select a chat to reply…'
                  : isClosed
                    ? 'This chat is closed.'
                    : 'Type your reply…'
              }
              disabled={!activeChat || isClosed}
              className="h-11 flex-1 rounded-lg border border-gray-300 bg-white px-4 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 disabled:opacity-60 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
            />
            <Button type="submit" disabled={!input.trim() || !activeChat || isClosed}>
              Send
            </Button>
          </div>
        </form>
      </main>
    </div>
  )
}
