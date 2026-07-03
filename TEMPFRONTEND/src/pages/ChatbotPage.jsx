import { useEffect, useRef, useState } from 'react'
import { Button, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { WS_BASE_URL } from '../utils/constants'

/**
 * Chatbot: a live WebSocket chat against the Django `ChatConsumer`.
 *
 * The user types a question -> it is sent over the socket -> the server embeds
 * it, finds the closest stored question, and sends back the single best match,
 * which we render as the bot's reply. No history is persisted (yet).
 */
export default function ChatbotPage() {
  const { user, logout } = useAuth()
  const companyId = user?.company

  const [messages, setMessages] = useState([]) // { id, role: 'user'|'bot', text, isError? }
  const [input, setInput] = useState('')
  const [status, setStatus] = useState('connecting') // connecting | open | closed
  const [waiting, setWaiting] = useState(false)

  const socketRef = useRef(null)
  const scrollRef = useRef(null)
  const idRef = useRef(0)

  const nextId = () => {
    idRef.current += 1
    return idRef.current
  }

  const pushMessage = (role, text, isError = false) =>
    setMessages((prev) => [...prev, { id: nextId(), role, text, isError }])

  // --- Open the socket once on mount -------------------------------------
  useEffect(() => {
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

      // `question` is the top match; falls back to the server's info message.
      const text = data.question || data.message || 'No matching question found.'
      pushMessage('bot', text)
    }

    return () => socket.close()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // --- Keep the latest message in view -----------------------------------
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, waiting])

  // --- Send a message ----------------------------------------------------
  const handleSend = (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || status !== 'open' || waiting) return

    pushMessage('user', text)
    socketRef.current.send(JSON.stringify({ message: text, company_id: companyId }))
    setInput('')
    setWaiting(true)
  }

  const statusLabel = {
    connecting: { text: 'Connecting…', tone: 'bg-amber-400' },
    open: { text: 'Connected', tone: 'bg-emerald-500' },
    closed: { text: 'Disconnected', tone: 'bg-red-500' },
  }[status]

  return (
    <div className="mx-auto flex h-screen max-w-2xl flex-col px-4 py-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Chatbot</h1>
          <div className="mt-0.5 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <span className={`inline-block h-2 w-2 rounded-full ${statusLabel.tone}`} />
            {statusLabel.text}
          </div>
        </div>
        <Button variant="secondary" onClick={logout}>
          Log out
        </Button>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-900/40"
      >
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-center text-sm text-gray-400">
            Ask a question to find the closest match from your knowledge base.
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={
                'max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ' +
                (m.role === 'user'
                  ? 'rounded-br-sm bg-brand-600 text-white'
                  : m.isError
                    ? 'rounded-bl-sm bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400'
                    : 'rounded-bl-sm bg-white text-gray-800 shadow-sm dark:bg-gray-800 dark:text-gray-100')
              }
            >
              {m.text}
            </div>
          </div>
        ))}

        {waiting && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-white px-4 py-2 text-sm text-gray-500 shadow-sm dark:bg-gray-800 dark:text-gray-400">
              <Spinner className="h-4 w-4" />
              Searching…
            </div>
          </div>
        )}
      </div>

      {/* Composer */}
      <form onSubmit={handleSend} className="mt-4 flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={status === 'open' ? 'Type your question…' : 'Connecting…'}
          disabled={status !== 'open'}
          className="h-11 flex-1 rounded-lg border border-gray-300 bg-white px-4 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 disabled:opacity-60 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
        />
        <Button type="submit" disabled={!input.trim() || status !== 'open' || waiting}>
          Send
        </Button>
      </form>
    </div>
  )
}
