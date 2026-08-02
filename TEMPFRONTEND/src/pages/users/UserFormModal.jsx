import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import { Button, Input, Modal, Select, Toggle } from '../../components/ui'
import { createUser, updateUser } from '../../redux/slices/userSlice'
import { addToast } from '../../redux/slices/uiSlice'
import { GENDER_OPTIONS, USER_TYPES, USER_TYPE_OPTIONS } from '../../utils/constants'

const EMPTY = {
  name: '',
  email: '',
  password: '',
  gender: '',
  dob: '',
  type: USER_TYPES.AGENT,
  active: true,
  is_archived: false,
}

/** Payload shape expected by `users.UserSerializer`. */
function buildPayload(values, companyId) {
  return {
    name: values.name.trim(),
    email: values.email.trim(),
    // Omitted on edit when left blank so the backend keeps the current hash.
    password: values.password?.trim() || undefined,
    gender: values.gender,
    dob: values.dob,
    company: companyId,
    type: values.type,
    active: values.active,
    is_archived: values.is_archived,
  }
}

export default function UserFormModal({ open, onClose, user, companyId, userType }) {
  const dispatch = useDispatch()
  const saving = useSelector((s) => s.users.saving)
  const isEdit = Boolean(user)

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm({ defaultValues: EMPTY })

  // The two booleans are rendered as <Toggle>s, so they are registered
  // manually and written through setValue.
  useEffect(() => {
    register('active')
    register('is_archived')
  }, [register])

  useEffect(() => {
    if (!open) return
    reset(
      user
        ? {
            name: user.name || '',
            email: user.email || '',
            password: '',
            gender: user.gender || '',
            dob: user.dob || '',
            type: user.type || USER_TYPES.AGENT,
            active: Boolean(user.active),
            is_archived: Boolean(user.is_archived),
          }
        : EMPTY,
    )
  }, [open, user, reset])

  const active = watch('active')
  const isArchived = watch('is_archived')

  const onSubmit = async (values) => {
    const payload = buildPayload(values, companyId)
    const result = isEdit
      ? await dispatch(updateUser({ id: user.id, payload, userType }))
      : await dispatch(createUser({ payload, userType }))

    const succeeded = isEdit
      ? updateUser.fulfilled.match(result)
      : createUser.fulfilled.match(result)

    if (succeeded) {
      dispatch(
        addToast({
          type: 'success',
          message: isEdit ? 'User updated successfully.' : 'User created successfully.',
        }),
      )
      onClose()
    } else {
      dispatch(addToast({ type: 'error', message: result.payload }))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={isEdit ? 'Edit user' : 'Create user'}
      description={isEdit ? `Editing #${user.id}` : 'Add a new team member'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button form="user-form" type="submit" loading={saving}>
            {isEdit ? 'Update user' : 'Create user'}
          </Button>
        </>
      }
    >
      <form
        id="user-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid grid-cols-1 gap-4 sm:grid-cols-2"
        noValidate
      >
        <Input
          label="Name"
          error={errors.name?.message}
          {...register('name', { required: 'Required' })}
        />
        <Input
          label="Email"
          type="email"
          error={errors.email?.message}
          {...register('email', {
            required: 'Required',
            pattern: {
              value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
              message: 'Enter a valid email address',
            },
          })}
        />
        <Input
          label={isEdit ? 'Password (leave blank to keep current)' : 'Password'}
          type="password"
          autoComplete="new-password"
          containerClassName="sm:col-span-2"
          error={errors.password?.message}
          {...register('password', {
            required: isEdit ? false : 'Required',
            minLength: { value: 6, message: 'Min 6 characters' },
          })}
        />
        <Select
          label="Gender"
          error={errors.gender?.message}
          {...register('gender', { required: 'Required' })}
        >
          <option value="">Select…</option>
          {GENDER_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
        <Input
          label="Date of birth"
          type="date"
          error={errors.dob?.message}
          {...register('dob', { required: 'Required' })}
        />
        <Select
          label="Type"
          containerClassName="sm:col-span-2"
          error={errors.type?.message}
          {...register('type', { required: 'Required' })}
        >
          {USER_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>

        <div className="space-y-4 rounded-xl border border-gray-200 p-4 sm:col-span-2 dark:border-gray-800">
          <Toggle
            checked={active}
            onChange={(v) => setValue('active', v, { shouldDirty: true })}
            label="Active"
            description="Inactive users cannot log in or be assigned chats."
          />
          <Toggle
            checked={isArchived}
            onChange={(v) => setValue('is_archived', v, { shouldDirty: true })}
            label="Archived"
            description="Archived users are hidden from agent assignment."
          />
        </div>
      </form>
    </Modal>
  )
}
