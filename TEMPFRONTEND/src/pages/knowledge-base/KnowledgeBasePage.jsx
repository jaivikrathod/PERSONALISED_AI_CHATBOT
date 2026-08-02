import { useCallback, useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import {
  BookOpenIcon,
  CheckCircleIcon,
  ClockIcon,
  CpuChipIcon,
  PlusIcon,
  QuestionMarkCircleIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import {
  Badge,
  Button,
  ConfirmDialog,
  PageHeader,
  SearchInput,
  StatCard,
  Table,
} from '../../components/ui'
import QuestionFormModal from './QuestionFormModal'
import useAuth from '../../hooks/useAuth'
import useDebounce from '../../hooks/useDebounce'
import { formatDate, truncate } from '../../utils/format'
import { addToast } from '../../redux/slices/uiSlice'
import {
  deleteQuestion,
  fetchQuestions,
  selectQuestionStats,
  setQuestionSearch,
  vectorizeQuestions,
} from '../../redux/slices/questionSlice'

/**
 * The company knowledge base: add question/answer pairs, then convert the
 * pending ones into vector embeddings so the chatbot can answer with them.
 */
export default function KnowledgeBasePage() {
  const dispatch = useDispatch()
  const { companyId } = useAuth()

  const { items, search, status, vectorizing } = useSelector((s) => s.questions)
  const stats = useSelector(selectQuestionStats)
  const unansweredCount = useSelector((s) => s.unanswered.items.length)

  const [searchInput, setSearchInput] = useState(search)
  const debouncedSearch = useDebounce(searchInput, 400)
  const [formOpen, setFormOpen] = useState(false)
  const [deleting, setDeleting] = useState(null)
  const [removing, setRemoving] = useState(false)

  useEffect(() => {
    dispatch(setQuestionSearch(debouncedSearch))
  }, [debouncedSearch, dispatch])

  const loadQuestions = useCallback(async () => {
    if (!companyId) return
    const result = await dispatch(fetchQuestions({ companyId, search }))
    if (fetchQuestions.rejected.match(result)) {
      dispatch(addToast({ type: 'error', message: result.payload }))
    }
  }, [dispatch, companyId, search])

  useEffect(() => {
    loadQuestions()
  }, [loadQuestions])

  const handleVectorize = async () => {
    const result = await dispatch(vectorizeQuestions(companyId))
    if (vectorizeQuestions.fulfilled.match(result)) {
      const { message, processed_questions, total_questions, failed_questions } =
        result.payload
      dispatch(
        addToast({
          type: failed_questions ? 'warning' : 'success',
          message:
            processed_questions != null
              ? `${message} Processed ${processed_questions}/${total_questions}, failed ${failed_questions}.`
              : message,
        }),
      )
      loadQuestions()
    } else {
      dispatch(addToast({ type: 'error', message: result.payload }))
    }
  }

  // Takes the row as an argument: reading `deleting.id` inside the closure
  // would make it a render-time memo dependency, which throws while null.
  const confirmDelete = async (question) => {
    if (!question) return
    setRemoving(true)
    const result = await dispatch(deleteQuestion(question.id))
    setRemoving(false)
    setDeleting(null)
    dispatch(
      addToast(
        deleteQuestion.fulfilled.match(result)
          ? { type: 'success', message: 'Question deleted.' }
          : { type: 'error', message: result.payload },
      ),
    )
  }

  const columns = [
    {
      key: 'question',
      header: 'Question',
      className: 'max-w-xs font-medium text-gray-900 dark:text-gray-100',
      render: (row) => <span className="line-clamp-2">{row.question}</span>,
    },
    {
      key: 'answer',
      header: 'Answer',
      className: 'max-w-sm text-gray-500 dark:text-gray-400',
      render: (row) => <span className="line-clamp-2">{truncate(row.answer, 120)}</span>,
    },
    {
      key: 'is_vectorized',
      header: 'Vector',
      render: (row) => (
        <Badge tone={row.is_vectorized ? 'green' : 'yellow'} dot>
          {row.is_vectorized ? 'Vectorized' : 'Pending'}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      headerClassName: 'whitespace-nowrap',
      render: (row) => (
        <span className="whitespace-nowrap text-gray-500">
          {formatDate(row.created_at)}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      headerClassName: 'text-right',
      className: 'text-right',
      render: (row) => (
        <button
          onClick={() => setDeleting(row)}
          title="Delete question"
          aria-label={`Delete question: ${truncate(row.question, 40)}`}
          className="rounded-lg p-2 text-gray-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10"
        >
          <TrashIcon className="h-4 w-4" />
        </button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Knowledge Base"
        subtitle="Manage the questions and answers that power your AI assistant."
      >
        <Button
          variant="secondary"
          onClick={handleVectorize}
          loading={vectorizing}
          disabled={items.length === 0}
        >
          {!vectorizing && <CpuChipIcon className="h-4 w-4" />}
          {vectorizing ? 'Vectorizing…' : 'Convert to vector'}
        </Button>
        <Button onClick={() => setFormOpen(true)}>
          <PlusIcon className="h-4 w-4" />
          Add question
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total questions"
          value={stats.total}
          icon={BookOpenIcon}
          color="brand"
          gradient
          loading={status === 'loading'}
        />
        <StatCard
          label="Vectorized"
          value={stats.vectorized}
          icon={CheckCircleIcon}
          color="green"
          loading={status === 'loading'}
        />
        <StatCard
          label="Pending vectorization"
          value={stats.pending}
          icon={ClockIcon}
          color="amber"
          loading={status === 'loading'}
        />
        <Link to="/unanswered" className="block transition hover:-translate-y-0.5">
          <StatCard
            label="Unanswered messages"
            value={unansweredCount}
            icon={QuestionMarkCircleIcon}
            color="slate"
          />
        </Link>
      </div>

      <div className="mb-4 mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchInput
          value={searchInput}
          onChange={setSearchInput}
          placeholder="Search questions…"
          className="w-full sm:max-w-sm"
        />
        <p className="text-sm text-gray-400">
          {stats.vectorized}/{stats.total} vectorized
        </p>
      </div>

      <Table
        columns={columns}
        data={items}
        loading={status === 'loading'}
        emptyTitle={search ? 'No matching questions' : 'No questions yet'}
        emptyDescription={
          search
            ? 'Try a different search term.'
            : 'Add your first question, then convert it to a vector so the chatbot can answer with it.'
        }
        emptyIcon={BookOpenIcon}
      />

      <QuestionFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        companyId={companyId}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        onClose={() => setDeleting(null)}
        onConfirm={() => confirmDelete(deleting)}
        loading={removing}
        title="Delete question"
        description={`Delete "${truncate(deleting?.question, 60)}"? It will be archived and its vector removed.`}
        confirmLabel="Delete"
      />
    </div>
  )
}
