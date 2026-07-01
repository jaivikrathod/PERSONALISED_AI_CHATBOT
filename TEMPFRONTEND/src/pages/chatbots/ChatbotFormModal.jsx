import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import { Modal, Button, Input, Select, Toggle } from '../../components/ui'
import { addToast } from '../../redux/slices/uiSlice'
import { createChatbot, updateChatbot } from '../../redux/slices/chatbotSlice'
import { Controller } from 'react-hook-form'

export default function ChatbotFormModal({ open, onClose, chatbot }) {
  const dispatch = useDispatch()
  const mutating = useSelector((s) => s.chatbots.mutating)
  const isEdit = Boolean(chatbot)

  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm({ defaultValues: { name: '', status: 'active', welcome_message: '' } })

  useEffect(() => {
    if (open) {
      reset({
        name: chatbot?.name || '',
        status: chatbot?.status || 'active',
        welcome_message: chatbot?.welcome_message || '',
      })
    }
  }, [open, chatbot, reset])

  const onSubmit = async (values) => {
    const payload = { ...values }
    const result = await dispatch(
      isEdit ? updateChatbot({ id: chatbot.id, payload }) : createChatbot(payload),
    )
    const ok =
      createChatbot.fulfilled.match(result) || updateChatbot.fulfilled.match(result)
    if (ok) {
      dispatch(addToast({ type: 'success', message: `Chatbot ${isEdit ? 'updated' : 'created'}.` }))
      onClose()
    } else {
      dispatch(addToast({ type: 'error', message: result.payload || 'Something went wrong.' }))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit Chatbot' : 'Create Chatbot'}
      description="Deploy an AI chatbot to a website or app via the widget."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={mutating}>
            Cancel
          </Button>
          <Button type="submit" form="bot-form" loading={mutating}>
            {isEdit ? 'Save changes' : 'Create Chatbot'}
          </Button>
        </>
      }
    >
      <form id="bot-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Chatbot name"
          placeholder="e.g. Website Support Bot"
          error={errors.name?.message}
          {...register('name', { required: 'Name is required' })}
        />
        <Input
          label="Welcome message"
          placeholder="Hi! How can I help you today?"
          {...register('welcome_message')}
        />
        <Controller
          control={control}
          name="status"
          render={({ field }) => (
            <div className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3 dark:border-gray-700">
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
                  Active
                </p>
                <p className="text-xs text-gray-400">
                  Inactive bots won&apos;t respond on your site.
                </p>
              </div>
              <Toggle
                checked={field.value === 'active'}
                onChange={(v) => field.onChange(v ? 'active' : 'inactive')}
              />
            </div>
          )}
        />
      </form>
    </Modal>
  )
}
