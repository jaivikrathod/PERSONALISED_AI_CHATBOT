import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import { SparklesIcon } from '@heroicons/react/24/outline'
import { Button, Modal, Textarea } from '../../components/ui'
import { resolveUnanswered } from '../../redux/slices/unansweredSlice'
import { addToast } from '../../redux/slices/uiSlice'

/**
 * Answer a message the chatbot couldn't handle. The backend turns it into a
 * Question, embeds it immediately and drops the row from the inbox — so the
 * answer starts serving similar questions right away.
 */
export default function AnswerQuestionModal({ open, onClose, message, onResolved }) {
  const dispatch = useDispatch()
  const resolvingId = useSelector((s) => s.unanswered.resolvingId)
  const saving = resolvingId === message?.id

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ defaultValues: { answer: '' } })

  useEffect(() => {
    if (open) reset({ answer: '' })
  }, [open, message?.id, reset])

  const onSubmit = async ({ answer }) => {
    if (!message) return
    const result = await dispatch(
      resolveUnanswered({ id: message.id, answer: answer.trim() }),
    )

    if (resolveUnanswered.fulfilled.match(result)) {
      dispatch(
        addToast({
          type: 'success',
          message:
            'Answer added and vectorized. It will now answer similar questions.',
        }),
      )
      onResolved?.()
      onClose()
    } else {
      dispatch(addToast({ type: 'error', message: result.payload }))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Answer this question"
      description="Your answer becomes a vectorized FAQ entry immediately."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button form="answer-form" type="submit" loading={saving}>
            {!saving && <SparklesIcon className="h-4 w-4" />}
            Add answer &amp; vectorize
          </Button>
        </>
      }
    >
      <div className="rounded-xl bg-gray-50 px-4 py-3 dark:bg-gray-800/60">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
          Customer asked
        </p>
        <p className="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
          {message?.message}
        </p>
      </div>

      <form
        id="answer-form"
        onSubmit={handleSubmit(onSubmit)}
        className="mt-4"
        noValidate
      >
        <Textarea
          label="Answer"
          rows={5}
          autoFocus
          placeholder="Type the answer for this question…"
          error={errors.answer?.message}
          {...register('answer', {
            required: 'An answer is required',
            validate: (v) => v.trim().length > 0 || 'Answer cannot be empty',
          })}
        />
      </form>
    </Modal>
  )
}
