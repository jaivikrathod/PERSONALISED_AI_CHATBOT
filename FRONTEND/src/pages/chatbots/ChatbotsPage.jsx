import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  PlusIcon,
  CpuChipIcon,
  PencilSquareIcon,
  TrashIcon,
  CodeBracketIcon,
  EllipsisHorizontalIcon,
} from '@heroicons/react/24/outline'
import {
  PageHeader,
  Button,
  Badge,
  Dropdown,
  Spinner,
  EmptyState,
  ConfirmDialog,
} from '../../components/ui'
import { STATUS_TONE } from '../../components/ui/Badge'
import ChatbotFormModal from './ChatbotFormModal'
import WidgetScriptModal from './WidgetScriptModal'
import { formatDate } from '../../utils/format'
import { addToast } from '../../redux/slices/uiSlice'
import {
  fetchChatbots,
  deleteChatbot,
} from '../../redux/slices/chatbotSlice'
import { mockChatbots } from '../../utils/mockData'

export default function ChatbotsPage() {
  const dispatch = useDispatch()
  const { items, status } = useSelector((s) => s.chatbots)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [scriptBot, setScriptBot] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [removing, setRemoving] = useState(false)

  useEffect(() => {
    dispatch(fetchChatbots())
  }, [dispatch])

  const usingMock = status !== 'loading' && items.length === 0
  // Guard against any null/malformed entries so the grid can never crash.
  const bots = (usingMock ? mockChatbots : items).filter(Boolean)

  const confirmDelete = async () => {
    setRemoving(true)
    const result = await dispatch(deleteChatbot(deleting.id))
    setRemoving(false)
    if (deleteChatbot.fulfilled.match(result)) {
      dispatch(addToast({ type: 'success', message: 'Chatbot deleted.' }))
    } else {
      dispatch(addToast({ type: 'error', message: result.payload || 'Delete failed.' }))
    }
    setDeleting(null)
  }

  return (
    <div>
      <PageHeader title="Chatbots" subtitle="Create and deploy AI chatbots across your channels.">
        <Button
          onClick={() => {
            setEditing(null)
            setFormOpen(true)
          }}
        >
          <PlusIcon className="h-4 w-4" />
          Create Chatbot
        </Button>
      </PageHeader>

      {status === 'loading' ? (
        <div className="flex justify-center py-20 text-brand-600">
          <Spinner className="h-8 w-8" />
        </div>
      ) : bots.length === 0 ? (
        <div className="card-base py-16">
          <EmptyState
            icon={CpuChipIcon}
            title="No chatbots yet"
            description="Create your first chatbot and embed it on your website."
            action={
              <Button onClick={() => setFormOpen(true)}>
                <PlusIcon className="h-4 w-4" />
                Create Chatbot
              </Button>
            }
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {bots.map((bot) => (
            <div key={bot.id ?? bot.uuid} className="card-base flex flex-col p-5 transition hover:shadow-card-hover">
              <div className="flex items-start justify-between">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 text-white shadow-sm">
                  <CpuChipIcon className="h-6 w-6" />
                </span>
                <Dropdown
                  trigger={
                    <button className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
                      <EllipsisHorizontalIcon className="h-5 w-5" />
                    </button>
                  }
                >
                  <Dropdown.Item
                    icon={CodeBracketIcon}
                    onClick={() => setScriptBot(bot)}
                  >
                    Widget script
                  </Dropdown.Item>
                  <Dropdown.Item
                    icon={PencilSquareIcon}
                    onClick={() => {
                      setEditing(bot)
                      setFormOpen(true)
                    }}
                  >
                    Edit
                  </Dropdown.Item>
                  <Dropdown.Divider />
                  <Dropdown.Item icon={TrashIcon} danger onClick={() => setDeleting(bot)}>
                    Delete
                  </Dropdown.Item>
                </Dropdown>
              </div>

              <h3 className="mt-4 text-base font-semibold text-gray-900 dark:text-gray-100">
                {bot.name}
              </h3>
              <div className="mt-1 flex items-center gap-2">
                <Badge tone={STATUS_TONE[bot.status]} dot>
                  {bot.status}
                </Badge>
                <span className="text-xs text-gray-400">
                  Created {formatDate(bot.created_at)}
                </span>
              </div>

              <div className="mt-4 rounded-lg bg-gray-50 px-3 py-2 dark:bg-gray-800/60">
                <p className="text-[11px] font-medium uppercase tracking-wide text-gray-400">
                  Widget Token
                </p>
                <p className="truncate font-mono text-xs text-gray-600 dark:text-gray-300">
                  {bot.widget_token}
                </p>
              </div>

              <Button
                variant="secondary"
                size="sm"
                className="mt-4 w-full"
                onClick={() => setScriptBot(bot)}
              >
                <CodeBracketIcon className="h-4 w-4" />
                Copy Widget Script
              </Button>
            </div>
          ))}
        </div>
      )}

      <ChatbotFormModal open={formOpen} onClose={() => setFormOpen(false)} chatbot={editing} />
      <WidgetScriptModal
        open={Boolean(scriptBot)}
        onClose={() => setScriptBot(null)}
        chatbot={scriptBot}
      />
      <ConfirmDialog
        open={Boolean(deleting)}
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
        loading={removing}
        title="Delete chatbot"
        description={`Delete "${deleting?.name}"? The widget will stop working immediately.`}
        confirmLabel="Delete"
      />
    </div>
  )
}
