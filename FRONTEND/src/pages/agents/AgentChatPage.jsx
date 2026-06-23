import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  UserGroupIcon,
  HandRaisedIcon,
  ArrowsRightLeftIcon,
  UserPlusIcon,
  CheckCircleIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/react/24/outline'
import {
  PageHeader,
  Button,
  Badge,
  Avatar,
  Card,
  EmptyState,
} from '../../components/ui'
import { STATUS_TONE } from '../../components/ui/Badge'
import MessageThread from '../../components/chat/MessageThread'
import MessageComposer from '../../components/chat/MessageComposer'
import ConversationListItem from '../../components/chat/ConversationListItem'
import AssignAgentModal from './AssignAgentModal'
import useConversationSocket from '../../hooks/useConversationSocket'
import { cn } from '../../utils/cn'
import { fetchAgents, takeOverConversation, resolveConversation } from '../../redux/slices/agentSlice'
import { fetchConversations, setActiveConversation } from '../../redux/slices/conversationSlice'
import { fetchMessages, sendMessage, messageReceived } from '../../redux/slices/chatSlice'
import { addToast } from '../../redux/slices/uiSlice'
import { mockAgents, mockConversations, mockMessages } from '../../utils/mockData'

export default function AgentChatPage() {
  const dispatch = useDispatch()
  const { items: agentList, status: agentStatus, acting } = useSelector((s) => s.agents)
  const { items: convItems, activeId, status: convStatus } = useSelector(
    (s) => s.conversations,
  )
  const chat = useSelector((s) => s.chat)

  const [taken, setTaken] = useState(false)
  const [modal, setModal] = useState(null) // 'assign' | 'transfer' | null

  useEffect(() => {
    dispatch(fetchAgents())
    dispatch(fetchConversations({ status: 'escalated' }))
  }, [dispatch])

  // Demo fallbacks
  const agents = agentStatus !== 'loading' && agentList.length === 0 ? mockAgents : agentList
  const usingMockConv = convStatus !== 'loading' && convItems.length === 0
  const conversations = usingMockConv ? mockConversations : convItems
  const effectiveActiveId = activeId || conversations[0]?.id
  const activeConv = conversations.find((c) => c.id === effectiveActiveId)

  useEffect(() => {
    if (effectiveActiveId && !usingMockConv) {
      dispatch(fetchMessages({ conversationId: effectiveActiveId }))
    }
  }, [dispatch, effectiveActiveId, usingMockConv])

  const { isPeerTyping, emitTyping } = useConversationSocket(
    usingMockConv ? null : effectiveActiveId,
    {
      onMessage: (message) =>
        dispatch(messageReceived({ conversationId: effectiveActiveId, message })),
    },
  )

  const bucket = chat.byConversation[effectiveActiveId]
  const messages = usingMockConv ? mockMessages : bucket?.messages || []

  const onlineAgents = agents.filter((a) => a.status === 'online').length

  const handleTakeOver = async () => {
    if (usingMockConv) {
      setTaken(true)
      dispatch(addToast({ type: 'success', message: 'You are now handling this chat.' }))
      return
    }
    const result = await dispatch(takeOverConversation(effectiveActiveId))
    if (takeOverConversation.fulfilled.match(result)) {
      setTaken(true)
      dispatch(addToast({ type: 'success', message: 'You took over the conversation.' }))
    }
  }

  const handleResolve = async () => {
    if (usingMockConv) {
      dispatch(addToast({ type: 'success', message: 'Conversation resolved.' }))
      return
    }
    const result = await dispatch(resolveConversation(effectiveActiveId))
    if (resolveConversation.fulfilled.match(result)) {
      dispatch(addToast({ type: 'success', message: 'Conversation resolved.' }))
    }
  }

  const handleSend = (body) => {
    if (usingMockConv) return
    dispatch(sendMessage({ conversationId: effectiveActiveId, body }))
  }

  return (
    <div>
      <PageHeader title="Live Agent Dashboard" subtitle="Handle escalated chats in real time.">
        <Badge tone="green" dot>
          {onlineAgents} agents online
        </Badge>
      </PageHeader>

      {/* Agent presence roster */}
      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {agents.map((a) => (
          <Card key={a.id} className="flex items-center gap-3 p-3.5">
            <Avatar name={a.name} status={a.status} src={a.avatar} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-gray-800 dark:text-gray-100">
                {a.name}
              </p>
              <p className="flex items-center gap-1.5 text-xs text-gray-400">
                <span className="capitalize">{a.status}</span>
                <span>·</span>
                <span>{a.active_chats} chats</span>
              </p>
            </div>
          </Card>
        ))}
      </div>

      {/* Workspace: queue + chat */}
      <div className="grid h-[calc(100vh-20rem)] min-h-[480px] grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Escalation queue */}
        <Card className="flex flex-col overflow-hidden lg:col-span-1">
          <div className="border-b border-gray-100 px-4 py-3 dark:border-gray-800">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Escalation Queue
            </h3>
          </div>
          <div className="flex-1 divide-y divide-gray-50 overflow-y-auto dark:divide-gray-800/60">
            {conversations.length === 0 ? (
              <EmptyState
                icon={CheckCircleIcon}
                title="Queue is clear"
                description="No chats are waiting for a human agent."
              />
            ) : (
              conversations.map((c) => (
                <ConversationListItem
                  key={c.id}
                  conversation={c}
                  active={c.id === effectiveActiveId}
                  onClick={() => {
                    dispatch(setActiveConversation(c.id))
                    setTaken(false)
                  }}
                />
              ))
            )}
          </div>
        </Card>

        {/* Chat + actions */}
        <Card className="flex flex-col overflow-hidden lg:col-span-2">
          {activeConv ? (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 px-4 py-3 dark:border-gray-800">
                <div className="flex items-center gap-3">
                  <Avatar name={activeConv.customer_name} status="online" />
                  <div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      {activeConv.customer_name}
                    </p>
                    <Badge tone={STATUS_TONE[activeConv.status]} dot>
                      {activeConv.status}
                    </Badge>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {!taken ? (
                    <Button size="sm" onClick={handleTakeOver} loading={acting}>
                      <HandRaisedIcon className="h-4 w-4" />
                      Take Over
                    </Button>
                  ) : (
                    <Badge tone="brand" dot>
                      You&apos;re handling this
                    </Badge>
                  )}
                  <Button size="sm" variant="secondary" onClick={() => setModal('assign')}>
                    <UserPlusIcon className="h-4 w-4" />
                    Assign
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => setModal('transfer')}>
                    <ArrowsRightLeftIcon className="h-4 w-4" />
                    Transfer
                  </Button>
                  <Button size="sm" variant="secondary" onClick={handleResolve}>
                    <CheckCircleIcon className="h-4 w-4" />
                    Resolve
                  </Button>
                </div>
              </div>

              <MessageThread
                messages={messages}
                loading={bucket?.loading}
                isPeerTyping={isPeerTyping}
                typingName={activeConv.customer_name}
              />

              <MessageComposer
                onSend={handleSend}
                onTyping={emitTyping}
                sending={chat.sending}
                disabled={!taken && !usingMockConv}
              />
              {!taken && !usingMockConv && (
                <p className="bg-amber-50 px-4 py-2 text-center text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
                  Take over the conversation to start replying.
                </p>
              )}
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <EmptyState
                icon={ChatBubbleLeftRightIcon}
                title="No chat selected"
                description="Pick a conversation from the escalation queue."
              />
            </div>
          )}
        </Card>
      </div>

      <AssignAgentModal
        open={Boolean(modal)}
        mode={modal}
        onClose={() => setModal(null)}
        conversationId={effectiveActiveId}
        agents={agents}
      />
    </div>
  )
}
