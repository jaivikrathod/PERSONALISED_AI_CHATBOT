import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  PlusIcon,
  ArrowUpTrayIcon,
  PencilSquareIcon,
  TrashIcon,
  BookOpenIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline'
import {
  PageHeader,
  Button,
  Badge,
  Table,
  Pagination,
  SearchInput,
  ConfirmDialog,
} from '../../components/ui'
import FaqFormModal from './FaqFormModal'
import BulkUploadModal from './BulkUploadModal'
import useDebounce from '../../hooks/useDebounce'
import { formatDate, truncate } from '../../utils/format'
import { addToast } from '../../redux/slices/uiSlice'
import {
  fetchFaqs,
  deleteFaq,
  setKbPage,
  setKbSearch,
  fetchEmbeddingStatus,
  generateEmbeddings,
} from '../../redux/slices/knowledgeBaseSlice'
import { mockFaqs } from '../../utils/mockData'

const EMBEDDING_BADGE = {
  READY: { tone: 'green', label: 'Vectorized' },
  PENDING: { tone: 'yellow', label: 'Pending' },
  FAILED: { tone: 'red', label: 'Failed' },
}

export default function KnowledgeBasePage() {
  const dispatch = useDispatch()
  const { items, count, page, pageSize, search, status, embedding, embeddingRunning } =
    useSelector((s) => s.kb)

  const [searchInput, setSearchInput] = useState(search)
  const debounced = useDebounce(searchInput, 400)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [bulkOpen, setBulkOpen] = useState(false)
  const [deleting, setDeleting] = useState(null)
  const [removing, setRemoving] = useState(false)

  useEffect(() => {
    dispatch(setKbSearch(debounced))
  }, [debounced, dispatch])

  useEffect(() => {
    dispatch(fetchFaqs({ search, page, pageSize }))
  }, [dispatch, search, page, pageSize])

  useEffect(() => {
    dispatch(fetchEmbeddingStatus())
  }, [dispatch])

  const handleConvert = async () => {
    const result = await dispatch(generateEmbeddings({ rebuild: false }))
    if (generateEmbeddings.fulfilled.match(result)) {
      const { embedded = 0, failed = 0 } = result.payload || {}
      dispatch(
        addToast({
          type: failed ? 'warning' : 'success',
          message: embedded
            ? `Vectorized ${embedded} FAQ${embedded === 1 ? '' : 's'}.${
                failed ? ` ${failed} failed.` : ''
              }`
            : 'All FAQs are already vectorized.',
        }),
      )
      dispatch(fetchEmbeddingStatus())
      dispatch(fetchFaqs({ search, page, pageSize }))
    } else {
      dispatch(
        addToast({ type: 'error', message: result.payload || 'Vectorization failed.' }),
      )
    }
  }

  // Demo fallback when the API has no data yet.
  const usingMock = status !== 'loading' && items.length === 0 && !search
  const rows = usingMock ? mockFaqs : items
  const total = usingMock ? mockFaqs.length : count

  const openCreate = () => {
    setEditing(null)
    setFormOpen(true)
  }
  const openEdit = (faq) => {
    setEditing(faq)
    setFormOpen(true)
  }

  const confirmDelete = async () => {
    if (!deleting) return
    setRemoving(true)
    const result = await dispatch(deleteFaq(deleting?.id))
    setRemoving(false)
    if (deleteFaq.fulfilled.match(result)) {
      dispatch(addToast({ type: 'success', message: 'FAQ deleted.' }))
    } else {
      dispatch(addToast({ type: 'error', message: result.payload || 'Delete failed.' }))
    }
    setDeleting(null)
  }

  const columns = [
    {
      key: 'question',
      header: 'Question',
      className: 'font-medium text-gray-900 dark:text-gray-100 max-w-xs',
      render: (r) => <span className="line-clamp-1">{r.question}</span>,
    },
    {
      key: 'answer',
      header: 'Answer',
      className: 'text-gray-500 dark:text-gray-400 max-w-sm',
      render: (r) => <span className="line-clamp-2">{truncate(r.answer, 90)}</span>,
    },
    {
      key: 'embedding_status',
      header: 'Vector',
      render: (r) => {
        const badge = EMBEDDING_BADGE[r.embedding_status] || EMBEDDING_BADGE.PENDING
        return (
          <Badge tone={badge.tone} dot>
            {badge.label}
          </Badge>
        )
      },
    },
    {
      key: 'created_at',
      header: 'Created',
      headerClassName: 'whitespace-nowrap',
      render: (r) => (
        <span className="whitespace-nowrap text-gray-500">{formatDate(r.created_at)}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      headerClassName: 'text-right',
      className: 'text-right',
      render: (r) => (
        <div className="flex items-center justify-end gap-1">
          <button
            onClick={() => openEdit(r)}
            className="rounded-lg p-2 text-gray-400 transition hover:bg-gray-100 hover:text-brand-600 dark:hover:bg-gray-800"
            title="Edit"
          >
            <PencilSquareIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => setDeleting(r)}
            className="rounded-lg p-2 text-gray-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10"
            title="Delete"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader title="Knowledge Base" subtitle="Manage the FAQs that power your AI assistant.">
        <Button
          variant="secondary"
          onClick={handleConvert}
          loading={embeddingRunning}
        >
          {!embeddingRunning && <CpuChipIcon className="h-4 w-4" />}
          {embeddingRunning ? 'Vectorizing…' : 'Convert to Vector DB'}
        </Button>
        <Button variant="secondary" onClick={() => setBulkOpen(true)}>
          <ArrowUpTrayIcon className="h-4 w-4" />
          Bulk Upload
        </Button>
        <Button onClick={openCreate}>
          <PlusIcon className="h-4 w-4" />
          Create FAQ
        </Button>
      </PageHeader>

      <div className="mb-4 flex items-center justify-between gap-3">
        <SearchInput
          value={searchInput}
          onChange={setSearchInput}
          placeholder="Search questions…"
          className="w-full max-w-sm"
        />
        <div className="hidden items-center gap-3 text-sm text-gray-400 sm:flex">
          {embedding.total > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="font-medium text-emerald-600 dark:text-emerald-400">
                {embedding.ready}
              </span>
              /{embedding.total} vectorized
              {embedding.failed > 0 && (
                <span className="text-red-500">· {embedding.failed} failed</span>
              )}
            </span>
          )}
          <span>{total} FAQs</span>
        </div>
      </div>

      <Table
        columns={columns}
        data={rows}
        loading={status === 'loading'}
        emptyTitle="No FAQs yet"
        emptyDescription="Create your first FAQ or bulk import from a spreadsheet."
        emptyIcon={BookOpenIcon}
      />

      {!usingMock && (
        <Pagination
          page={page}
          pageSize={pageSize}
          total={total}
          onChange={(p) => dispatch(setKbPage(p))}
        />
      )}

      <FaqFormModal open={formOpen} onClose={() => setFormOpen(false)} faq={editing} />
      <BulkUploadModal open={bulkOpen} onClose={() => setBulkOpen(false)} />
      <ConfirmDialog
        open={Boolean(deleting)}
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
        loading={removing}
        title="Delete FAQ"
        description={`Are you sure you want to delete "${truncate(deleting?.question, 60)}"? This can't be undone.`}
        confirmLabel="Delete"
      />
    </div>
  )
}
