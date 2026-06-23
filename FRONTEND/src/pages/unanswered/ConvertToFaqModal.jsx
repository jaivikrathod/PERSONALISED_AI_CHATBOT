import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import { Modal, Button, Input, Textarea } from '../../components/ui'
import { addToast } from '../../redux/slices/uiSlice'
import { convertUnanswered } from '../../redux/slices/analyticsSlice'

/** Converts an unanswered question into a knowledge-base FAQ. */
export default function ConvertToFaqModal({ open, onClose, question }) {
  const dispatch = useDispatch()
  const status = useSelector((s) => s.analytics.status)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ defaultValues: { question: '', answer: '' } })

  // Prefill the question text when opened.
  useEffect(() => {
    if (open) reset({ question: question?.question || '', answer: '' })
  }, [open, question, reset])

  const onSubmit = async (values) => {
    const result = await dispatch(
      convertUnanswered({ id: question.id, payload: values }),
    )
    if (convertUnanswered.fulfilled.match(result)) {
      dispatch(addToast({ type: 'success', message: 'Added to knowledge base.' }))
      onClose()
    } else {
      dispatch(addToast({ type: 'error', message: result.payload || 'Conversion failed.' }))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Convert to FAQ"
      description="Answer this question once and let the AI handle it from now on."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="convert-form" loading={status === 'loading'}>
            Add to Knowledge Base
          </Button>
        </>
      }
    >
      <form id="convert-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Question"
          error={errors.question?.message}
          {...register('question', { required: 'Question is required' })}
        />
        <Textarea
          label="Answer"
          rows={6}
          placeholder="Write the answer the AI should give…"
          error={errors.answer?.message}
          {...register('answer', { required: 'Answer is required' })}
        />
      </form>
    </Modal>
  )
}
