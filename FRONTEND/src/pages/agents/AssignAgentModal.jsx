import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Modal, Button, Avatar } from '../../components/ui'
import { cn } from '../../utils/cn'
import { addToast } from '../../redux/slices/uiSlice'
import {
  assignConversation,
  transferConversation,
} from '../../redux/slices/agentSlice'

/** Shared picker for Assign / Transfer actions. `mode` = 'assign' | 'transfer'. */
export default function AssignAgentModal({ open, onClose, mode, conversationId, agents }) {
  const dispatch = useDispatch()
  const acting = useSelector((s) => s.agents.acting)
  const [selected, setSelected] = useState(null)
  const isTransfer = mode === 'transfer'

  const submit = async () => {
    if (!selected) return
    const action = isTransfer
      ? transferConversation({ conversationId, agentId: selected })
      : assignConversation({ conversationId, agentId: selected })
    const result = await dispatch(action)
    const ok =
      transferConversation.fulfilled.match(result) ||
      assignConversation.fulfilled.match(result)
    dispatch(
      addToast(
        ok
          ? { type: 'success', message: `Conversation ${isTransfer ? 'transferred' : 'assigned'}.` }
          : { type: 'error', message: result.payload || 'Action failed.' },
      ),
    )
    if (ok) onClose()
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isTransfer ? 'Transfer conversation' : 'Assign conversation'}
      description={`Choose an agent to ${isTransfer ? 'transfer' : 'assign'} this conversation to.`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={acting} disabled={!selected}>
            {isTransfer ? 'Transfer' : 'Assign'}
          </Button>
        </>
      }
    >
      <div className="space-y-1.5">
        {agents.map((a) => (
          <button
            key={a.id}
            onClick={() => setSelected(a.id)}
            className={cn(
              'flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition',
              selected === a.id
                ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/10'
                : 'border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800',
            )}
          >
            <Avatar name={a.name} status={a.status} />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-800 dark:text-gray-100">{a.name}</p>
              <p className="text-xs text-gray-400 capitalize">
                {a.status} · {a.active_chats} active
              </p>
            </div>
            {selected === a.id && (
              <span className="h-2.5 w-2.5 rounded-full bg-brand-600" />
            )}
          </button>
        ))}
      </div>
    </Modal>
  )
}
