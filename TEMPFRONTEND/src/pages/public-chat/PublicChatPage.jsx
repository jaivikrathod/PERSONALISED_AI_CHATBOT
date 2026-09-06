import { useCallback, useEffect, useMemo, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useParams } from 'react-router-dom'
import {
  ArrowPathIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline'
import { Badge, Button, EmptyState, Spinner } from '../../components/ui'
import ConnectionStatus from '../../components/chat/ConnectionStatus'
import MessageBubble from '../../components/chat/MessageBubble'
import MessageComposer from '../../components/chat/MessageComposer'
import MessageThread from '../../components/chat/MessageThread'
import ThemeToggle from '../../components/layout/ThemeToggle'
import PreChatForm from './PreChatForm'
import useCustomerChatSocket from '../../hooks/useCustomerChatSocket'
import chatbotService from '../../services/chatbotService'
import { SOCKET_STATUS } from '../../utils/constants'
import {
  clearStoredSessionId,
  getStoredGuest,
  getStoredSessionId,
  storeGuest,
  storeSessionId,
} from '../../utils/guestChat'
import {
  fetchHistory,
  resetCustomerChat,
  sessionEstablished,
  startNewChat,
} from '../../redux/slices/customerChatSlice'

/** Maps a stored message onto the shared <MessageBubble> props. */
function bubbleProps(message) {
  if (message.sender === 'system') return { tone: 'system' }
  if (message.role === 'user') return { tone: 'brand', outbound: true }
  if (message.isError) return { tone: 'error' }
  if (message.sender === 'agent') return { tone: 'human', author: 'Support agent' }
  return { tone: 'ai', author: 'Assistant' }
}

/**
 * The shareable, public-facing chatbot at `/chat/:companyId`.
 *
 * Deliberately outside the dashboard shell and outside every auth guard: the
 * whole point is that a company can hand this URL to anyone. Questions go down
 * the `ws/chat/` socket, are matched against that company's vectorized FAQs,
 * and are handed to a human agent when the AI cannot answer them confidently.
 */
export default function PublicChatPage() {
  const dispatch = useDispatch()
  const { companyId } = useParams()

  // Company lookup: 'loading' -> 'ready' | 'missing'.
  const [config, setConfig] = useState({ state: 'loading', name: '' })
  const [guest, setGuest] = useState(null)

  const {
    activeSessionId,
    messages,
    socketStatus,
    waiting,
    loadingMessages,
    agentHandling,
    closed,
  } = useSelector((s) => s.customerChat)

  const { sendMessage } = useCustomerChatSocket({
    // Hold the socket back until we know the company exists and the visitor
    // has been through the pre-chat step.
    companyId: config.state === 'ready' && guest ? companyId : null,
    customerUserName: guest?.name,
    customerUserEmail: guest?.email,
  })

  // Resolve the company behind the link, and restore this browser's previous
  // conversation with it (if any).
  useEffect(() => {
    let cancelled = false
    dispatch(resetCustomerChat())

    chatbotService
      .getWidgetConfig({ companyId })
      .then((data) => {
        if (cancelled) return
        setConfig({ state: 'ready', name: data.company_name })

        const storedSessionId = getStoredSessionId(companyId)
        const storedGuest = getStoredGuest()
        // A visitor who already has a thread here skips the pre-chat form.
        if (storedSessionId || storedGuest) setGuest(storedGuest || {})
        if (storedSessionId) dispatch(sessionEstablished(storedSessionId))
      })
      .catch(() => {
        if (!cancelled) setConfig({ state: 'missing', name: '' })
      })

    return () => {
      cancelled = true
      dispatch(resetCustomerChat())
    }
  }, [dispatch, companyId])

  // Replay the conversation whenever we (re)attach to a session.
  useEffect(() => {
    if (activeSessionId) dispatch(fetchHistory({ sessionId: activeSessionId, companyId }))
  }, [dispatch, activeSessionId, companyId])

  // Keep localStorage in step so a reload lands back in the same thread.
  useEffect(() => {
    if (activeSessionId) storeSessionId(companyId, activeSessionId)
    else clearStoredSessionId(companyId)
  }, [companyId, activeSessionId])

  const handleStart = useCallback((details) => {
    storeGuest(details)
    setGuest(details)
  }, [])

  const handleNewChat = useCallback(() => {
    clearStoredSessionId(companyId)
    dispatch(startNewChat())
  }, [dispatch, companyId])

  const handleSend = useCallback((text) => sendMessage(text), [sendMessage])

  const isConnected = socketStatus === SOCKET_STATUS.OPEN
  const canSend = isConnected && !waiting && !loadingMessages

  const subtitle = useMemo(() => {
    if (closed) return 'This conversation was closed — send a message to start a new one.'
    if (agentHandling) return 'A support agent is handling this conversation.'
    return 'Answers come from our knowledge base, with a human on standby.'
  }, [closed, agentHandling])

  if (config.state === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 text-brand-600 dark:bg-gray-950">
        <Spinner className="h-8 w-8" />
      </div>
    )
  }

  if (config.state === 'missing') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-950">
        <EmptyState
          icon={ExclamationTriangleIcon}
          title="Chat unavailable"
          description="This chat link is not valid. Please check the address with whoever shared it with you."
        />
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50 dark:bg-gray-950">
      <header className="flex items-center gap-2 border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-900 sm:gap-3 sm:px-6">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 text-white">
          {agentHandling ? (
            <UserCircleIcon className="h-5 w-5" />
          ) : (
            <SparklesIcon className="h-5 w-5" />
          )}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
            {config.name}
          </p>
          <p className="truncate text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>
        </div>
        {agentHandling && (
          <Badge tone="green" dot className="hidden shrink-0 sm:inline-flex">
            Live agent
          </Badge>
        )}
        {guest && <ConnectionStatus status={socketStatus} className="hidden sm:flex" />}
        {guest && messages.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleNewChat}
            title="Start a new conversation"
          >
            <ArrowPathIcon className="h-4 w-4" />
            <span className="hidden sm:inline">New chat</span>
          </Button>
        )}
        <ThemeToggle />
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col overflow-hidden border-gray-200 dark:border-gray-800 sm:border-x">
        {!guest ? (
          <PreChatForm companyName={config.name} onStart={handleStart} />
        ) : (
          <>
            <MessageThread
              loading={loadingMessages}
              isEmpty={messages.length === 0}
              emptyIcon={SparklesIcon}
              emptyTitle="Ask your first question"
              emptyDescription="Your question is matched against our knowledge base — if we cannot answer it, a support agent takes over."
              pending={waiting}
              pendingName={agentHandling ? 'Support agent' : 'Assistant'}
              pendingLabel={agentHandling ? 'Waiting for the agent…' : 'Searching…'}
              scrollKey={messages.length}
            >
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  body={message.text}
                  {...bubbleProps(message)}
                />
              ))}
            </MessageThread>

            <MessageComposer
              onSend={handleSend}
              disabled={!canSend}
              placeholder={
                isConnected ? 'Type your question…' : 'Connecting to the assistant…'
              }
            />
          </>
        )}
      </main>
    </div>
  )
}
