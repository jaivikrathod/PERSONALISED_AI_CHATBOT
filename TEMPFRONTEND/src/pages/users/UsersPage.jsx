import { useCallback, useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  PencilSquareIcon,
  PlusIcon,
  TrashIcon,
  UsersIcon,
} from '@heroicons/react/24/outline'
import {
  Avatar,
  Badge,
  Button,
  ConfirmDialog,
  PageHeader,
  SearchInput,
  Table,
} from '../../components/ui'
import UserFormModal from './UserFormModal'
import { formatDate } from '../../utils/format'
import { addToast } from '../../redux/slices/uiSlice'
import { deleteUser, fetchUsers } from '../../redux/slices/userSlice'

const TYPE_TONE = {
  Admin: 'brand',
  Manager: 'blue',
  Agent: 'gray',
}

/** Company user management — Admin and Manager only (enforced by RoleRoute). */
export default function UsersPage() {
  const dispatch = useDispatch()
  const { items, status, deletingId } = useSelector((s) => s.users)

  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState(null)
  const [formOpen, setFormOpen] = useState(false)
  const [deleting, setDeleting] = useState(null)

  const load = useCallback(async () => {
    const result = await dispatch(fetchUsers())
    if (fetchUsers.rejected.match(result)) {
      dispatch(addToast({ type: 'error', message: result.payload }))
    }
  }, [dispatch])

  useEffect(() => {
    load()
  }, [load])

  const openCreate = () => {
    setEditing(null)
    setFormOpen(true)
  }

  const openEdit = (user) => {
    setEditing(user)
    setFormOpen(true)
  }

  // Takes the row as an argument: reading `deleting.id` inside the closure
  // would make it a render-time memo dependency, which throws while null.
  const confirmDelete = async (target) => {
    if (!target) return
    const result = await dispatch(deleteUser({ id: target.id }))
    setDeleting(null)
    dispatch(
      addToast(
        deleteUser.fulfilled.match(result)
          ? { type: 'success', message: 'User deleted successfully.' }
          : { type: 'error', message: result.payload },
      ),
    )
  }

  // Client-side filter — the list is scoped to one company and stays small.
  const term = search.trim().toLowerCase()
  const rows = term
    ? items.filter(
        (user) =>
          user.name?.toLowerCase().includes(term) ||
          user.email?.toLowerCase().includes(term),
      )
    : items

  const columns = [
    {
      key: 'name',
      header: 'User',
      render: (row) => (
        <div className="flex items-center gap-3">
          <Avatar name={row.name} size="sm" status={row.active ? 'online' : 'offline'} />
          <div className="min-w-0">
            <p className="truncate font-medium text-gray-900 dark:text-gray-100">
              {row.name}
            </p>
            <p className="truncate text-xs text-gray-400">{row.email}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Role',
      render: (row) => <Badge tone={TYPE_TONE[row.type] || 'gray'}>{row.type}</Badge>,
    },
    {
      key: 'gender',
      header: 'Gender',
      render: (row) => <span className="text-gray-500">{row.gender || '—'}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge tone={row.active ? 'green' : 'gray'} dot>
            {row.active ? 'Active' : 'Inactive'}
          </Badge>
          {row.is_archived && <Badge tone="yellow">Archived</Badge>}
        </div>
      ),
    },
    {
      key: 'created_at',
      header: 'Joined',
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
        <div className="flex items-center justify-end gap-1">
          <button
            onClick={() => openEdit(row)}
            title="Edit"
            aria-label={`Edit ${row.name}`}
            className="rounded-lg p-2 text-gray-400 transition hover:bg-gray-100 hover:text-brand-600 dark:hover:bg-gray-800"
          >
            <PencilSquareIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => setDeleting(row)}
            title="Delete"
            aria-label={`Delete ${row.name}`}
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
      <PageHeader title="Users" subtitle="Manage the people in your company workspace.">
        <Button onClick={openCreate}>
          <PlusIcon className="h-4 w-4" />
          New user
        </Button>
      </PageHeader>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search by name or email…"
          className="w-full sm:max-w-sm"
        />
        <p className="text-sm text-gray-400">
          {rows.length} {rows.length === 1 ? 'user' : 'users'}
        </p>
      </div>

      <Table
        columns={columns}
        data={rows}
        loading={status === 'loading'}
        emptyTitle={term ? 'No matching users' : 'No users yet'}
        emptyDescription={
          term ? 'Try a different search term.' : 'Create the first user for your company.'
        }
        emptyIcon={UsersIcon}
      />

      <UserFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        user={editing}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        onClose={() => setDeleting(null)}
        onConfirm={() => confirmDelete(deleting)}
        loading={deletingId === deleting?.id}
        title="Delete user"
        description={`Delete ${deleting?.name}? This cannot be undone.`}
        confirmLabel="Delete"
      />
    </div>
  )
}
