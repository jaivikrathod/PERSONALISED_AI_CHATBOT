import { useCallback, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  BellAlertIcon,
  CheckCircleIcon,
  ChatBubbleLeftRightIcon,
  InboxIcon,
} from '@heroicons/react/24/outline'
import { Badge, Button, Card, EmptyState, PageHeader, Spinner } from '../../components/ui'
import ConnectionStatus from '../../components/chat/ConnectionStatus'
import ConversationListItem from '../../components/chat/ConversationListItem'
import MessageBubble from '../../components/chat/MessageBubble'
import MessageComposer from '../../components/chat/MessageComposer'
import MessageThread from '../../components/chat/MessageThread'
import useAuth from '../../hooks/useAuth'
import useAgentSocket from '../../hooks/useAgentSocket'
import { SESSION_STATUS } from '../../utils/constants'
import {
  chatOpened,
  alertDismissed,
  clearAgentError,
  closeAgentChat,
  fetchAgentChats,
  fetchAgentHistory,
  selectActiveChat,
  selectOpenChatCount,
  sendAgentMessage,
} from '../../redux/slices/agentChatSlice'

const SENDER_VIEW = {
  customer: { tone: 'neutral', outbound: false },
  ai: { tone: 'ai', outbound: true, author: 'AI' },
  agent: { tone: 'brand', outbound: true, author: 'You' },
}

/**
 * Human-agent console. Chats the bot could not answer are assigned here in
 * real time; replies go out over the socket and fall back to REST when it is
 * down. Access is limited to Agent-type users by the route guard.
 */
export default function AgentConsolePage() {
  const dispatch = useDispatch()
  const { user } = useAuth()
  const agentId = user?.id

  const {
    chats,
    activeSessionId,
    messages,
    unread,
    alert,
    socketStatus,
    loadingChats,
    loadingMessages,
    error,
  } = useSelector((s) => s.agentChat)

  const activeChat = useSelector(selectActiveChat)
  const openChatCount = useSelector(selectOpenChatCount)
  const isClosed = activeChat?.status === SESSION_STATUS.CLOSED

  const { sendMessage, closeChat } = useAgentSocket(agentId)

  // REST first so the inbox renders even if the socket is unavailable.
  useEffect(() => {
    if (agentId) dispatch(fetchAgentChats(agentId))
  }, [dispatch, agentId])

  const openChat = useCallback(
    (sessionId) => {
      dispatch(chatOpened(sessionId))
      dispatch(fetchAgentHistory({ agentId, sessionId }))
    },
    [dispatch, agentId],
  )

  /** Socket first; the REST endpoint is the fallback when it dropped. */
  const handleSend = useCallback(
    (text) => {
      if (sendMessage(activeSessionId, text)) return true
      dispatch(sendAgentMessage({ agentId, sessionId: activeSessionId, message: text }))
      return true
    },
    [dispatch, sendMessage, agentId, activeSessionId],
  )

  const handleClose = useCallback(() => {
    if (!activeSessionId) return
    if (closeChat(activeSessionId)) return
    dispatch(closeAgentChat({ agentId, sessionId: activeSessionId }))
  }, [dispatch, closeChat, agentId, activeSessionId])

  return (
    <div>
      <PageHeader
        title="Agent Console"
        subtitle="Answer the conversations the AI handed over to you."
      >
        <Badge tone={openChatCount ? 'green' : 'gray'} dot>
          {openChatCount} live {openChatCount === 1 ? 'chat' : 'chats'}
        </Badge>
        <ConnectionStatus status={socketStatus} />
      </PageHeader>

      {alert && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-brand-200 bg-brand-50 px-4 py-3 text-sm animate-slide-up dark:border-brand-500/30 dark:bg-brand-500/10">
          <span className="flex items-center gap-2 font-medium text-brand-700 dark:text-brand-300">
            <BellAlertIcon className="h-5 w-5 shrink-0" />
            New chat assigned to you — Chat #{alert.sessionId}
          </span>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => openChat(alert.sessionId)}>
              Take chat
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => dispatch(alertDismissed())}
            >
              Dismiss
            </Button>
          </div>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="mb-4 flex items-start justify-between gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400"
        >
          <span>{error}</span>
          <button
            onClick={() => dispatch(clearAgentError())}
            className="shrink-0 font-medium hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="grid h-[calc(100vh-16rem)] min-h-[480px] grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Assigned chats */}
        <Card className="flex flex-col overflow-hidden lg:col-span-1">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-800">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Assigned chats
            </h2>
            {loadingChats && <Spinner className="h-4 w-4 text-gray-400" />}
          </div>
          <div className="flex-1 divide-y divide-gray-50 overflow-y-auto dark:divide-gray-800/60">
            {!loadingChats && chats.length === 0 ? (
              <EmptyState
                icon={InboxIcon}
                title="No chats assigned yet"
                description="You'll be notified the moment one arrives."
              />
            ) : (
              chats.map((chat) => (
                <ConversationListItem
                  key={chat.id}
                  title={`Chat #${chat.id}`}
                  preview={chat.last_message}
                  status={chat.status}
                  updatedAt={chat.last_message_at}
                  unread={Boolean(unread[chat.id])}
                  active={chat.id === activeSessionId}
                  onClick={() => openChat(chat.id)}
                />
              ))
            )}
          </div>
        </Card>

        {/* Conversation */}
        <Card className="flex flex-col overflow-hidden lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 px-4 py-3 dark:border-gray-800">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
                {activeChat ? `Chat #${activeChat.id}` : 'No conversation selected'}
              </p>
              <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                {activeChat
                  ? isClosed
                    ? 'This conversation is closed.'
                    : 'You are answering this customer — the AI is paused.'
                  : 'Pick a chat from the list to start answering.'}
              </p>
            </div>
            {activeChat && !isClosed && (
              <Button size="sm" variant="secondary" onClick={handleClose}>
                <CheckCircleIcon className="h-4 w-4" />
                Close chat
              </Button>
            )}
          </div>

          <MessageThread
            loading={loadingMessages}
            isEmpty={!activeChat || messages.length === 0}
            emptyIcon={ChatBubbleLeftRightIcon}
            emptyTitle={activeChat ? 'No messages yet' : 'Nothing selected'}
            emptyDescription={
              activeChat
                ? 'Say hello — the customer is waiting for a human.'
                : "When the bot cannot answer a question, the chat is assigned to a free agent and shows up here instantly."
            }
            scrollKey={messages.length}
          >
            {messages.map((message) => {
              const view = SENDER_VIEW[message.sender] || SENDER_VIEW.customer
              return (
                <MessageBubble
                  key={message.id}
                  body={message.text}
                  createdAt={message.createdAt}
                  {...view}
                  author={
                    message.sender === 'customer'
                      ? message.customerName || 'Customer'
                      : view.author
                  }
                />
              )
            })}
          </MessageThread>

          <MessageComposer
            onSend={handleSend}
            disabled={!activeChat || isClosed}
            placeholder={
              !activeChat
                ? 'Select a chat to reply…'
                : isClosed
                  ? 'This chat is closed.'
                  : 'Type your reply…'
            }
          />
        </Card>
      </div>
    </div>
  )
}
