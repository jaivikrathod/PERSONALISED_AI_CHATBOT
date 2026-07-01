import { useEffect, useMemo, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  ChatBubbleLeftRightIcon,
  ArrowLeftIcon,
  EllipsisVerticalIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import {
  SearchInput,
  Badge,
  Avatar,
  Spinner,
  EmptyState,
  Dropdown,
} from '../../components/ui'
import { STATUS_TONE } from '../../components/ui/Badge'
import MessageThread from '../../components/chat/MessageThread'
import MessageComposer from '../../components/chat/MessageComposer'
import ConversationListItem from '../../components/chat/ConversationListItem'
import useDebounce from '../../hooks/useDebounce'
import useConversationSocket from '../../hooks/useConversationSocket'
import { cn } from '../../utils/cn'
import { CONVERSATION_STATUS_OPTIONS } from '../../utils/constants'
import {
  fetchConversations,
  setActiveConversation,
  setConversationSearch,
  setStatusFilter,
  updateConversationStatus,
  conversationBumped,
} from '../../redux/slices/conversationSlice'
import {
  fetchMessages,
  loadMoreMessages,
  sendMessage,
  messageReceived,
} from '../../redux/slices/chatSlice'
import { addToast } from '../../redux/slices/uiSlice'
import { mockConversations, mockMessages } from '../../utils/mockData'

export default function ConversationsPage() {
  const dispatch = useDispatch()
  const {
    items,
    activeId,
    statusFilter,
    status: listStatus,
  } = useSelector((s) => s.conversations)
  const chat = useSelector((s) => s.chat)

  const [searchInput, setSearchInput] = useState('')
  const debounced = useDebounce(searchInput, 400)
  const [mobileThread, setMobileThread] = useState(false)

  // --- data ----
  useEffect(() => {
    dispatch(setConversationSearch(debounced))
  }, [debounced, dispatch])

  useEffect(() => {
    dispatch(fetchConversations({ search: debounced, status: statusFilter }))
  }, [dispatch, debounced, statusFilter])

  // Demo fallback
  const usingMock = listStatus !== 'loading' && items.length === 0
  const conversations = usingMock ? mockConversations : items
  const effectiveActiveId = activeId || conversations[0]?.id

  useEffect(() => {
    if (effectiveActiveId && !usingMock) {
      dispatch(fetchMessages({ conversationId: effectiveActiveId }))
    }
  }, [dispatch, effectiveActiveId, usingMock])

  // --- realtime ----
  useConversationSocket(usingMock ? null : effectiveActiveId, {
    onMessage: (message) => {
      dispatch(messageReceived({ conversationId: effectiveActiveId, message }))
      dispatch(
        conversationBumped({
          conversationId: effectiveActiveId,
          lastMessage: message.body,
          incrementUnread: false,
        }),
      )
    },
  })
  const { isPeerTyping, emitTyping } = useConversationSocket(
    usingMock ? null : effectiveActiveId,
  )

  const filtered = useMemo(() => {
    if (!searchInput) return conversations
    return conversations.filter((c) =>
      c.customer_name?.toLowerCase().includes(searchInput.toLowerCase()),
    )
  }, [conversations, searchInput])

  const activeConv = conversations.find((c) => c.id === effectiveActiveId)
  const bucket = chat.byConversation[effectiveActiveId]
  const messages = usingMock ? mockMessages : bucket?.messages || []

  const selectConversation = (id) => {
    dispatch(setActiveConversation(id))
    setMobileThread(true)
  }

  const handleSend = (body) => {
    if (usingMock) {
      dispatch(addToast({ type: 'info', message: 'Connect the API to send live messages.' }))
      return
    }
    dispatch(sendMessage({ conversationId: effectiveActiveId, body }))
  }

  const changeStatus = (newStatus) => {
    dispatch(updateConversationStatus({ id: effectiveActiveId, status: newStatus }))
    dispatch(addToast({ type: 'success', message: `Marked as ${newStatus}.` }))
  }

  const unreadTotal = conversations.reduce((s, c) => s + (c.unread_count || 0), 0)

  return (
    <div className="h-[calc(100vh-7rem)] overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-card dark:border-gray-800 dark:bg-gray-900">
      <div className="flex h-full">
        {/* LEFT — conversation list */}
        <div
          className={cn(
            'flex w-full flex-col border-r border-gray-200 dark:border-gray-800 md:w-80 lg:w-96',
            mobileThread && 'hidden md:flex',
          )}
        >
          <div className="border-b border-gray-100 p-4 dark:border-gray-800">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-base font-semibold text-gray-900 dark:text-gray-100">
                Inbox
                {unreadTotal > 0 && (
                  <span className="rounded-full bg-brand-600 px-2 py-0.5 text-xs font-bold text-white">
                    {unreadTotal}
                  </span>
                )}
              </h2>
            </div>
            <SearchInput
              value={searchInput}
              onChange={setSearchInput}
              placeholder="Search conversations…"
            />
            <div className="no-scrollbar mt-3 flex gap-1.5 overflow-x-auto">
              {CONVERSATION_STATUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => dispatch(setStatusFilter(opt.value))}
                  className={cn(
                    'whitespace-nowrap rounded-full px-3 py-1 text-xs font-medium transition',
                    statusFilter === opt.value
                      ? 'bg-brand-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300',
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 divide-y divide-gray-50 overflow-y-auto dark:divide-gray-800/60">
            {listStatus === 'loading' && !usingMock ? (
              <div className="flex justify-center py-16 text-brand-600">
                <Spinner className="h-6 w-6" />
              </div>
            ) : filtered.length === 0 ? (
              <EmptyState
                icon={ChatBubbleLeftRightIcon}
                title="No conversations"
                description="New conversations from your widget will appear here."
              />
            ) : (
              filtered.map((c) => (
                <ConversationListItem
                  key={c.id}
                  conversation={c}
                  active={c.id === effectiveActiveId}
                  onClick={() => selectConversation(c.id)}
                />
              ))
            )}
          </div>
        </div>

        {/* RIGHT — message thread */}
        <div className={cn('flex flex-1 flex-col', !mobileThread && 'hidden md:flex')}>
          {activeConv ? (
            <>
              <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-800">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setMobileThread(false)}
                    className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 md:hidden"
                  >
                    <ArrowLeftIcon className="h-5 w-5" />
                  </button>
                  <Avatar name={activeConv.customer_name} size="md" />
                  <div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      {activeConv.customer_name}
                    </p>
                    <div className="flex items-center gap-2">
                      <Badge tone={STATUS_TONE[activeConv.status]} dot>
                        {activeConv.status}
                      </Badge>
                      <span className="text-xs text-gray-400 capitalize">
                        via {activeConv.channel || 'widget'}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => changeStatus('resolved')}
                    className="hidden items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800 sm:inline-flex"
                  >
                    <CheckCircleIcon className="h-4 w-4" />
                    Resolve
                  </button>
                  <Dropdown
                    trigger={
                      <button className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
                        <EllipsisVerticalIcon className="h-5 w-5" />
                      </button>
                    }
                  >
                    <Dropdown.Item onClick={() => changeStatus('open')}>
                      Mark as open
                    </Dropdown.Item>
                    <Dropdown.Item onClick={() => changeStatus('pending')}>
                      Mark as pending
                    </Dropdown.Item>
                    <Dropdown.Item onClick={() => changeStatus('escalated')}>
                      Escalate
                    </Dropdown.Item>
                    <Dropdown.Item onClick={() => changeStatus('resolved')}>
                      Resolve
                    </Dropdown.Item>
                  </Dropdown>
                </div>
              </div>

              <MessageThread
                messages={messages}
                loading={bucket?.loading}
                hasMore={bucket?.hasMore}
                onLoadMore={() =>
                  dispatch(
                    loadMoreMessages({
                      conversationId: effectiveActiveId,
                      before: messages[0]?.id,
                    }),
                  )
                }
                isPeerTyping={isPeerTyping}
                typingName={activeConv.customer_name}
              />

              <MessageComposer
                onSend={handleSend}
                onTyping={emitTyping}
                sending={chat.sending}
              />
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <EmptyState
                icon={ChatBubbleLeftRightIcon}
                title="Select a conversation"
                description="Choose a conversation from the list to view messages."
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
