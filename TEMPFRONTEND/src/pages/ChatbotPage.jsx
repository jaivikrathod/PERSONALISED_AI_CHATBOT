import { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import chatbotService from '../services/chatbotService'
import { WS_BASE_URL } from '../utils/constants'

export default function ChatbotPage() {
  const { user, logout } = useAuth()
  const companyId = user?.company
  const customerUserId = user?.id
  const customerUserName = user?.name
  const customerUserEmail = user?.email

  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState('connecting')
  const [waiting, setWaiting] = useState(false)
  const [loadingSessions, setLoadingSessions] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)

  const socketRef = useRef(null)
  const scrollRef = useRef(null)
  const idRef = useRef(0)

  const nextId = () => {
    idRef.current += 1
    return idRef.current
  }

  const pushMessage = (role, text, isError = false) =>
    setMessages((prev) => [...prev, { id: nextId(), role, text, isError }])

  const refreshSessions = async (preferredSessionId = null) => {
    const data = await chatbotService.listSessions({ companyId, customerUserId })
    setSessions(data)
    const nextActive = preferredSessionId || activeSessionId || data[0]?.id || null
    setActiveSessionId(nextActive)
    return data
  }

  const loadSession = async (sessionId) => {
    if (!sessionId) {
      setMessages([])
      return
    }

    setLoadingMessages(true)
    try {
      const data = await chatbotService.getHistory({
        sessionId,
        companyId,
        customerUserId,
      })
      const restoredMessages = (data.messages || []).map((message) => ({
        id: message.id,
        role: message.role,
        text: message.message,
        isError: false,
      }))
      setMessages(restoredMessages)
    } finally {
      setLoadingMessages(false)
    }
  }

  useEffect(() => {
    let mounted = true

    const bootstrap = async () => {
      try {
        setLoadingSessions(true)
        const data = await chatbotService.listSessions({ companyId, customerUserId })
        if (!mounted) return
        setSessions(data)
        const firstSessionId = data[0]?.id || null
        setActiveSessionId(firstSessionId)
        if (firstSessionId) {
          await loadSession(firstSessionId)
        } else {
          setMessages([])
        }
      } catch {
        if (mounted) {
          setSessions([])
          setActiveSessionId(null)
          setMessages([])
        }
      } finally {
        if (mounted) setLoadingSessions(false)
      }
    }

    bootstrap()

    const socket = new WebSocket(`${WS_BASE_URL}/ws/chat/`)
    socketRef.current = socket

    socket.onopen = () => setStatus('open')
    socket.onclose = () => setStatus('closed')
    socket.onerror = () => setStatus('closed')

    socket.onmessage = (event) => {
      setWaiting(false)
      let data
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }

      if (data.type === 'error') {
        pushMessage('bot', data.error || 'Something went wrong.', true)
        return
      }

      const nextSessionId = data.session_id || activeSessionId
      if (nextSessionId && nextSessionId !== activeSessionId) {
        setActiveSessionId(nextSessionId)
        refreshSessions(nextSessionId).catch(() => {})
      } else {
        refreshSessions(nextSessionId).catch(() => {})
      }

      pushMessage('bot', data.answer || data.message || 'No matching question found.')
    }

    return () => {
      mounted = false
      socket.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, waiting, loadingMessages])

  useEffect(() => {
    if (activeSessionId) {
      loadSession(activeSessionId).catch(() => {})
    } else {
      setMessages([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId])

  const handleSend = (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || status !== 'open' || waiting || loadingSessions || loadingMessages) return

    pushMessage('user', text)
    socketRef.current.send(
      JSON.stringify({
        message: text,
        company_id: companyId,
        customer_user_id: customerUserId,
        customer_user_name: customerUserName,
        customer_user_email: customerUserEmail,
        session_id: activeSessionId,
      }),
    )
    setInput('')
    setWaiting(true)
  }

  const statusLabel = useMemo(
    () =>
      ({
        connecting: { text: 'Connectingâ€¦', tone: 'bg-amber-400' },
        open: { text: 'Connected', tone: 'bg-emerald-500' },
        closed: { text: 'Disconnected', tone: 'bg-red-500' },
      })[status],
    [status],
  )

  const activeSession = sessions.find((session) => session.id === activeSessionId)

  return (
    <div className="flex h-screen bg-gray-100 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <aside className="flex w-80 flex-col border-r border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
        <div className="border-b border-gray-200 px-4 py-4 dark:border-gray-800">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold">Chatbot</h1>
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
              Conversations
            </span>
            {loadingSessions && <Spinner className="h-4 w-4 text-gray-400" />}
          </div>

          <div className="space-y-2">
            {sessions.map((session) => {
              const isActive = session.id === activeSessionId
              return (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => setActiveSessionId(session.id)}
                  className={
                    'w-full rounded-xl border px-3 py-3 text-left transition ' +
                    (isActive
                      ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/10'
                      : 'border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-800 dark:bg-gray-900 dark:hover:bg-gray-800')
                  }
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="truncate text-sm font-medium">
                      Chat #{session.id}
                    </div>
                    <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                      {session.messages?.length || 0} msgs
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {session.last_message || 'No messages yet.'}
                  </div>
                </button>
              )
            })}

            {!loadingSessions && sessions.length === 0 && (
              <div className="rounded-xl border border-dashed border-gray-300 px-3 py-6 text-center text-sm text-gray-400 dark:border-gray-700">
                No chat history yet.
              </div>
            )}
          </div>
        </div>
      </aside>

      <main className="flex flex-1 flex-col">
        <div className="border-b border-gray-200 bg-white px-5 py-4 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold">
                {activeSession ? `Chat #${activeSession.id}` : 'New Chat'}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {activeSession?.last_message_at
                  ? new Date(activeSession.last_message_at).toLocaleString()
                  : 'Start a new conversation'}
              </p>
            </div>
          </div>
        </div>

        <div
          ref={scrollRef}
          className="flex-1 space-y-3 overflow-y-auto bg-gray-50 p-4 dark:bg-gray-950"
        >
          {loadingMessages && (
            <div className="flex h-full items-center justify-center text-sm text-gray-400">
              Loading chat history...
            </div>
          )}

          {!loadingMessages && messages.length === 0 && (
            <div className="flex h-full items-center justify-center text-center text-sm text-gray-400">
              Ask a question to find the closest match from your knowledge base.
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={
                  'max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ' +
                  (message.role === 'user'
                    ? 'rounded-br-sm bg-brand-600 text-white'
                    : message.isError
                      ? 'rounded-bl-sm bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400'
                      : 'rounded-bl-sm bg-white text-gray-800 shadow-sm dark:bg-gray-800 dark:text-gray-100')
                }
              >
                {message.text}
              </div>
            </div>
          ))}

          {waiting && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-white px-4 py-2 text-sm text-gray-500 shadow-sm dark:bg-gray-800 dark:text-gray-400">
                <Spinner className="h-4 w-4" />
                Searchingâ€¦
              </div>
            </div>
          )}
        </div>

        <form onSubmit={handleSend} className="border-t border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={status === 'open' ? 'Type your questionâ€¦' : 'Connectingâ€¦'}
              disabled={status !== 'open' || loadingSessions || loadingMessages}
              className="h-11 flex-1 rounded-lg border border-gray-300 bg-white px-4 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 disabled:opacity-60 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
            />
            <Button type="submit" disabled={!input.trim() || status !== 'open' || waiting || loadingSessions || loadingMessages}>
              Send
            </Button>
          </div>
        </form>
      </main>
    </div>
  )
}
