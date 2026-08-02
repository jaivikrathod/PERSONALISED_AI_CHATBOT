import { useCallback, useEffect, useMemo } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  ChatBubbleLeftRightIcon,
  SparklesIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline'
import { Badge, Card, EmptyState, PageHeader, Spinner } from '../../components/ui'
import ConnectionStatus from '../../components/chat/ConnectionStatus'
import ConversationListItem from '../../components/chat/ConversationListItem'
import MessageBubble from '../../components/chat/MessageBubble'
import MessageComposer from '../../components/chat/MessageComposer'
import MessageThread from '../../components/chat/MessageThread'
import useAuth from '../../hooks/useAuth'
import useCustomerChatSocket from '../../hooks/useCustomerChatSocket'
import { formatDateTime } from '../../utils/format'
import { SOCKET_STATUS } from '../../utils/constants'
import {
  fetchHistory,
  fetchSessions,
  resetCustomerChat,
  sessionSelected,
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
 * Customer-facing chatbot. Questions go down the `ws/chat/` socket, are matched
 * against the company's vectorized FAQs, and are handed to a human agent when
 * the AI can't answer them confidently.
 */
export default function ChatbotPage() {
  const dispatch = useDispatch()
  const { user, companyId } = useAuth()

  const {
    sessions,
    activeSessionId,
    messages,
    socketStatus,
    waiting,
    loadingSessions,
    loadingMessages,
    agentHandling,
  } = useSelector((s) => s.customerChat)

  const { sendMessage } = useCustomerChatSocket({
    companyId,
    customerUserId: user?.id,
    customerUserName: user?.name,
    customerUserEmail: user?.email,
  })

  // Initial inbox load; the socket keeps it fresh from there.
  useEffect(() => {
    if (!companyId || !user?.id) return undefined
    dispatch(fetchSessions({ companyId, customerUserId: user.id }))
    return () => dispatch(resetCustomerChat())
  }, [dispatch, companyId, user?.id])

  // Whenever the selection changes, replay that conversation from the server.
  useEffect(() => {
    if (activeSessionId) dispatch(fetchHistory({ sessionId: activeSessionId, companyId }))
  }, [dispatch, activeSessionId, companyId])

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) || null,
    [sessions, activeSessionId],
  )

  const isConnected = socketStatus === SOCKET_STATUS.OPEN
  const canSend = isConnected && !waiting && !loadingSessions && !loadingMessages

  const handleSend = useCallback((text) => sendMessage(text), [sendMessage])

  const subtitle = agentHandling
    ? 'A support agent is handling this conversation.'
    : activeSession?.last_message_at
      ? formatDateTime(activeSession.last_message_at)
      : 'Start a new conversation'

  return (
    <div>
      <PageHeader
        title="Chatbot"
        subtitle="Ask a question and get the closest match from your knowledge base."
      >
        <ConnectionStatus status={socketStatus} />
      </PageHeader>

      <div className="grid h-[calc(100vh-14rem)] min-h-[480px] grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Conversation history */}
        <Card className="hidden flex-col overflow-hidden lg:col-span-1 lg:flex">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-800">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Conversations
            </h2>
            {loadingSessions && <Spinner className="h-4 w-4 text-gray-400" />}
          </div>
          <div className="flex-1 divide-y divide-gray-50 overflow-y-auto dark:divide-gray-800/60">
            {!loadingSessions && sessions.length === 0 ? (
              <EmptyState
                icon={ChatBubbleLeftRightIcon}
                title="No chat history yet"
                description="Send your first message to start a conversation."
              />
            ) : (
              sessions.map((session) => (
                <ConversationListItem
                  key={session.id}
                  title={`Chat #${session.id}`}
                  preview={session.last_message}
                  status={session.status}
                  updatedAt={session.last_message_at}
                  active={session.id === activeSessionId}
                  onClick={() => dispatch(sessionSelected(session.id))}
                />
              ))
            )}
          </div>
        </Card>

        {/* Thread */}
        <Card className="flex flex-col overflow-hidden lg:col-span-2">
          <div className="flex items-center gap-3 border-b border-gray-100 px-4 py-3 dark:border-gray-800">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 text-white">
              {agentHandling ? (
                <UserCircleIcon className="h-5 w-5" />
              ) : (
                <SparklesIcon className="h-5 w-5" />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
                {activeSession ? `Chat #${activeSession.id}` : 'New chat'}
              </p>
              <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                {subtitle}
              </p>
            </div>
            {agentHandling && (
              <Badge tone="green" dot className="shrink-0">
                Live agent
              </Badge>
            )}
          </div>

          <MessageThread
            loading={loadingMessages}
            isEmpty={messages.length === 0}
            emptyIcon={SparklesIcon}
            emptyTitle="Ask your first question"
            emptyDescription="Your question is matched against the company knowledge base — if the AI can't answer it, a support agent takes over."
            pending={waiting}
            pendingName={agentHandling ? 'Support agent' : 'Assistant'}
            pendingLabel={agentHandling ? 'Waiting for the agent…' : 'Searching…'}
            scrollKey={messages.length}
          >
            {messages.map((message) => (
              <MessageBubble key={message.id} body={message.text} {...bubbleProps(message)} />
            ))}
          </MessageThread>

          <MessageComposer
            onSend={handleSend}
            disabled={!canSend}
            placeholder={
              isConnected ? 'Type your question…' : 'Connecting to the assistant…'
            }
          />
        </Card>
      </div>
    </div>
  )
}
