import { useCallback, useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  QuestionMarkCircleIcon,
  SparklesIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { Button, ConfirmDialog, PageHeader, Table } from '../../components/ui'
import AnswerQuestionModal from './AnswerQuestionModal'
import useAuth from '../../hooks/useAuth'
import { timeAgo, truncate } from '../../utils/format'
import { addToast } from '../../redux/slices/uiSlice'
import { fetchQuestions } from '../../redux/slices/questionSlice'
import { dismissUnanswered, fetchUnanswered } from '../../redux/slices/unansweredSlice'

/**
 * Inbox of customer messages the chatbot could not answer from the FAQ
 * database. Answering one creates a vectorized Question; dismissing drops it.
 */
export default function UnansweredPage() {
  const dispatch = useDispatch()
  const { companyId } = useAuth()
  const { items, status } = useSelector((s) => s.unanswered)

  const [answering, setAnswering] = useState(null)
  const [dismissing, setDismissing] = useState(null)
  const [removing, setRemoving] = useState(false)

  const load = useCallback(async () => {
    if (!companyId) return
    const result = await dispatch(fetchUnanswered(companyId))
    if (fetchUnanswered.rejected.match(result)) {
      dispatch(addToast({ type: 'error', message: result.payload }))
    }
  }, [dispatch, companyId])

  useEffect(() => {
    load()
  }, [load])

  // Takes the row as an argument: reading `dismissing.id` inside the closure
  // would make it a render-time memo dependency, which throws while null.
  const confirmDismiss = async (message) => {
    if (!message) return
    setRemoving(true)
    const result = await dispatch(dismissUnanswered(message.id))
    setRemoving(false)
    setDismissing(null)
    if (dismissUnanswered.rejected.match(result)) {
      dispatch(addToast({ type: 'error', message: result.payload }))
    }
  }

  const columns = [
    {
      key: 'message',
      header: 'Question',
      className: 'max-w-xl font-medium text-gray-900 dark:text-gray-100',
      render: (row) => <span className="line-clamp-2">{row.message}</span>,
    },
    {
      key: 'timestamp',
      header: 'Asked',
      headerClassName: 'whitespace-nowrap',
      render: (row) => (
        <span className="whitespace-nowrap text-gray-500">{timeAgo(row.timestamp)}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      headerClassName: 'text-right',
      className: 'text-right',
      render: (row) => (
        <div className="flex items-center justify-end gap-1">
          <Button size="sm" variant="subtle" onClick={() => setAnswering(row)}>
            <SparklesIcon className="h-4 w-4" />
            Answer
          </Button>
          <button
            onClick={() => setDismissing(row)}
            title="Dismiss without answering"
            aria-label={`Dismiss: ${truncate(row.message, 40)}`}
            className="rounded-lg p-2 text-gray-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Unanswered Questions"
        subtitle="Questions customers asked that weren't in your knowledge base — answer one to close the gap."
      />

      <Table
        columns={columns}
        data={items}
        loading={status === 'loading'}
        emptyTitle="Nothing unanswered"
        emptyDescription="Your knowledge base is covering everything customers ask. 🎉"
        emptyIcon={QuestionMarkCircleIcon}
      />

      <AnswerQuestionModal
        open={Boolean(answering)}
        onClose={() => setAnswering(null)}
        message={answering}
        // A new vectorized question was created — keep the KB list in sync.
        onResolved={() => dispatch(fetchQuestions({ companyId }))}
      />

      <ConfirmDialog
        open={Boolean(dismissing)}
        onClose={() => setDismissing(null)}
        onConfirm={() => confirmDismiss(dismissing)}
        loading={removing}
        title="Dismiss question"
        description={`Dismiss "${truncate(dismissing?.message, 60)}" without answering it? It will be removed from the inbox.`}
        confirmLabel="Dismiss"
      />
    </div>
  )
}
