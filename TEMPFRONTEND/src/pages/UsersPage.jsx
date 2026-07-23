import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Button, Card, CardBody, CardHeader, EmptyState, Input, Select, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { USER_TYPES, GENDER_OPTIONS } from '../utils/constants'
import api from '../services/axiosInstance'

function buildPayload(values, companyId, existingUser) {
  return {
    name: values.name.trim(),
    email: values.email.trim(),
    password: values.password?.trim() || undefined,
    gender: values.gender,
    dob: values.dob,
    company: companyId,
    type: values.type,
    active: values.active,
    is_archived: values.is_archived,
    ...(existingUser ? {} : {}),
  }
}

export default function UsersPage() {
  const { user, logout } = useAuth()
  const companyId = user?.company
  const userType = user?.type
  const canManage = [USER_TYPES.ADMIN, USER_TYPES.MANAGER].includes(userType)

  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [editingUser, setEditingUser] = useState(null)
  const [banner, setBanner] = useState('')

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      name: '',
      email: '',
      password: '',
      gender: '',
      dob: '',
      type: USER_TYPES.AGENT,
      active: true,
      is_archived: false,
    },
  })

  const loadUsers = async () => {
    setLoading(true)
    setBanner('')
    try {
      const { data } = await api.get('/managed-users/', {
        params: { company_id: companyId, user_type: userType },
      })
      setUsers(data)
    } catch (error) {
      setBanner(error.message || 'Failed to load users.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!canManage) {
      setLoading(false)
      return
    }
    loadUsers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId, userType])

  const startCreate = () => {
    setEditingUser(null)
    reset({
      name: '',
      email: '',
      password: '',
      gender: '',
      dob: '',
      type: USER_TYPES.AGENT,
      active: true,
      is_archived: false,
    })
  }

  const startEdit = (item) => {
    setEditingUser(item)
    reset({
      name: item.name || '',
      email: item.email || '',
      password: '',
      gender: item.gender || '',
      dob: item.dob || '',
      type: item.type || USER_TYPES.AGENT,
      active: Boolean(item.active),
      is_archived: Boolean(item.is_archived),
    })
  }

  const onSubmit = async (values) => {
    setSaving(true)
    setBanner('')
    try {
      const payload = buildPayload(values, companyId, editingUser)
      if (editingUser) {
        await api.put(`/managed-users/${editingUser.id}/`, payload, {
          params: { user_type: userType },
        })
        setBanner('User updated successfully.')
      } else {
        await api.post('/managed-users/', payload, {
          params: { user_type: userType },
        })
        setBanner('User created successfully.')
      }
      await loadUsers()
      startCreate()
    } catch (error) {
      setBanner(error.message || 'Failed to save user.')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Delete ${item.name}?`)) return
    setDeletingId(item.id)
    setBanner('')
    try {
      await api.delete(`/managed-users/${item.id}/`, {
        params: { user_type: userType },
      })
      setBanner('User deleted successfully.')
      await loadUsers()
      if (editingUser?.id === item.id) startCreate()
    } catch (error) {
      setBanner(error.message || 'Failed to delete user.')
    } finally {
      setDeletingId(null)
    }
  }

  if (!canManage) {
    return (
      <div className="mx-auto flex min-h-screen max-w-2xl items-center justify-center px-4">
        <Card className="w-full">
          <CardBody>
            <EmptyState
              title="Access denied"
              description="Only Admin and Manager users can manage users."
              action={<Button onClick={logout}>Log out</Button>}
            />
          </CardBody>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Users</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage company users. Signed in as {user?.name} ({userType})
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={logout}>
            Log out
          </Button>
          <Button variant="secondary" onClick={startCreate}>
            New user
          </Button>
        </div>
      </div>

      {banner && (
        <div className="mb-4 rounded-lg bg-gray-900 px-4 py-3 text-sm text-white dark:bg-gray-800">
          {banner}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <Card>
          <CardHeader
            title={editingUser ? 'Edit user' : 'Create user'}
            subtitle={editingUser ? `Editing #${editingUser.id}` : 'Add a new team member'}
          />
          <CardBody>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <Input label="Name" error={errors.name?.message} {...register('name', { required: 'Required' })} />
              <Input label="Email" type="email" error={errors.email?.message} {...register('email', { required: 'Required' })} />
              <Input
                label={editingUser ? 'Password (leave blank to keep current)' : 'Password'}
                type="password"
                error={errors.password?.message}
                {...register('password', {
                  required: editingUser ? false : 'Required',
                  minLength: { value: 6, message: 'Min 6 characters' },
                })}
              />
              <Select label="Gender" error={errors.gender?.message} {...register('gender', { required: 'Required' })}>
                <option value="">Select...</option>
                {GENDER_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
              <Input label="Date of birth" type="date" error={errors.dob?.message} {...register('dob', { required: 'Required' })} />
              <Select label="Type" error={errors.type?.message} {...register('type', { required: 'Required' })}>
                <option value={USER_TYPES.AGENT}>Agent</option>
                <option value={USER_TYPES.MANAGER}>Manager</option>
                <option value={USER_TYPES.ADMIN}>Admin</option>
              </Select>
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input type="checkbox" {...register('active')} />
                Active
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input type="checkbox" {...register('is_archived')} />
                Archived
              </label>
              <Button type="submit" loading={isSubmitting || saving} className="w-full">
                {editingUser ? 'Update user' : 'Create user'}
              </Button>
            </form>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title={`Users (${users.length})`} subtitle="Click a row to edit or delete it" />
          <CardBody>
            {loading ? (
              <div className="flex justify-center py-10">
                <Spinner className="h-6 w-6" />
              </div>
            ) : users.length === 0 ? (
              <EmptyState title="No users yet" description="Create the first user using the form on the left." />
            ) : (
              <div className="space-y-3">
                {users.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-xl border border-gray-200 p-4 dark:border-gray-800"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {item.name}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">{item.email}</div>
                        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                          {item.type} · {item.gender} · {item.active ? 'Active' : 'Inactive'}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="secondary" onClick={() => startEdit(item)}>
                          Edit
                        </Button>
                        <Button
                          variant="secondary"
                          onClick={() => handleDelete(item)}
                          loading={deletingId === item.id}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
