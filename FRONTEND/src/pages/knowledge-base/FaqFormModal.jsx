import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import { Modal, Button, Input, Textarea } from '../../components/ui'
import { addToast } from '../../redux/slices/uiSlice'
import { createFaq, updateFaq } from '../../redux/slices/knowledgeBaseSlice'

/** Create / edit FAQ. Pass `faq` to edit, omit to create. */
export default function FaqFormModal({ open, onClose, faq }) {
  const dispatch = useDispatch()
  const mutating = useSelector((s) => s.kb.mutating)
  const isEdit = Boolean(faq)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ defaultValues: { question: '', answer: '' } })

  useEffect(() => {
    if (open) reset({ question: faq?.question || '', answer: faq?.answer || '' })
  }, [open, faq, reset])

  const onSubmit = async (values) => {
    const action = isEdit
      ? updateFaq({ id: faq.id, payload: values })
      : createFaq(values)
    const result = await dispatch(action)
    if (action.type.startsWith('kb') && (createFaq.fulfilled.match(result) || updateFaq.fulfilled.match(result))) {
      dispatch(addToast({ type: 'success', message: `FAQ ${isEdit ? 'updated' : 'created'}.` }))
      onClose()
    } else {
      dispatch(addToast({ type: 'error', message: result.payload || 'Something went wrong.' }))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit FAQ' : 'Create FAQ'}
      description="Questions & answers power your AI's automatic resolutions."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={mutating}>
            Cancel
          </Button>
          <Button type="submit" form="faq-form" loading={mutating}>
            {isEdit ? 'Save changes' : 'Create FAQ'}
          </Button>
        </>
      }
    >
      <form id="faq-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Question"
          placeholder="e.g. How do I reset my password?"
          error={errors.question?.message}
          {...register('question', {
            required: 'Question is required',
            minLength: { value: 5, message: 'Too short' },
          })}
        />
        <Textarea
          label="Answer"
          rows={6}
          placeholder="Write a clear, helpful answer…"
          error={errors.answer?.message}
          {...register('answer', {
            required: 'Answer is required',
            minLength: { value: 5, message: 'Too short' },
          })}
        />
      </form>
    </Modal>
  )
}
