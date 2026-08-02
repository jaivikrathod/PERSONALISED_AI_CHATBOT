import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import { Button, Input, Modal, Textarea } from '../../components/ui'
import { createQuestion } from '../../redux/slices/questionSlice'
import { addToast } from '../../redux/slices/uiSlice'

const EMPTY = { question: '', answer: '' }

/**
 * Create a question/answer pair. New pairs start un-vectorized — the page's
 * "Convert to vector" action embeds every pending row in one pass.
 */
export default function QuestionFormModal({ open, onClose, companyId }) {
  const dispatch = useDispatch()
  const mutating = useSelector((s) => s.questions.mutating)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ defaultValues: EMPTY })

  useEffect(() => {
    if (open) reset(EMPTY)
  }, [open, reset])

  const onSubmit = async ({ question, answer }) => {
    const result = await dispatch(
      createQuestion({
        companyId,
        question: question.trim(),
        answer: answer.trim(),
      }),
    )

    if (createQuestion.fulfilled.match(result)) {
      dispatch(addToast({ type: 'success', message: 'Question added.' }))
      onClose()
    } else {
      dispatch(addToast({ type: 'error', message: result.payload }))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add a question"
      description="Create a Q&A pair for your company."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={mutating}>
            Cancel
          </Button>
          <Button form="question-form" type="submit" loading={mutating}>
            Add question
          </Button>
        </>
      }
    >
      <form
        id="question-form"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        noValidate
      >
        <Input
          label="Question"
          placeholder="What is your refund policy?"
          error={errors.question?.message}
          {...register('question', {
            required: 'A question is required',
            validate: (v) => v.trim().length > 0 || 'A question is required',
          })}
        />
        <Textarea
          label="Answer"
          rows={4}
          placeholder="Refunds are processed within 7 business days."
          error={errors.answer?.message}
          {...register('answer', {
            required: 'An answer is required',
            validate: (v) => v.trim().length > 0 || 'An answer is required',
          })}
        />
      </form>
    </Modal>
  )
}
