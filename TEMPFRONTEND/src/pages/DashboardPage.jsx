import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Input,
  Textarea,
  Card,
  CardHeader,
  CardBody,
  Badge,
  Spinner,
  EmptyState,
} from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { questionService } from '../services/questionService'
import { vectorService } from '../services/vectorService'

/**
 * Step 2 (main): add question/answer pairs, then convert them to vectors.
 */
export default function DashboardPage() {
  const { user, logout } = useAuth()
  const companyId = user?.company

  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ question: '', answer: '' })
  const [saving, setSaving] = useState(false)
  const [vectorizing, setVectorizing] = useState(false)
  const [banner, setBanner] = useState(null) // { type: 'success'|'error', text }

  // --- Load questions -----------------------------------------------------
  const loadQuestions = useCallback(async () => {
    setLoading(true)
    try {
      const data = await questionService.list(companyId)
      setQuestions(data)
    } catch (err) {
      setBanner({ type: 'error', text: err.message || 'Failed to load questions.' })
    } finally {
      setLoading(false)
    }
  }, [companyId])

  useEffect(() => {
    loadQuestions()
  }, [loadQuestions])

  // --- Add a question -----------------------------------------------------
  const handleAdd = async (e) => {
    e.preventDefault()
    if (!form.question.trim() || !form.answer.trim()) return
    setSaving(true)
    setBanner(null)
    try {
      await questionService.create({
        companyId,
        question: form.question.trim(),
        answer: form.answer.trim(),
      })
      setForm({ question: '', answer: '' })
      await loadQuestions()
    } catch (err) {
      setBanner({ type: 'error', text: err.message || 'Failed to add question.' })
    } finally {
      setSaving(false)
    }
  }

  // --- Delete a question --------------------------------------------------
  const handleDelete = async (id) => {
    try {
      await questionService.remove(id)
      await loadQuestions()
    } catch (err) {
      setBanner({ type: 'error', text: err.message || 'Failed to delete question.' })
    }
  }

  // --- Convert to vector --------------------------------------------------
  const handleVectorize = async () => {
    setVectorizing(true)
    setBanner(null)
    try {
      const result = await vectorService.vectorizeCompany(companyId)
      const text =
        result.processed_questions != null
          ? `${result.message} Processed ${result.processed_questions}/${result.total_questions}, failed ${result.failed_questions}.`
          : result.message
      setBanner({ type: 'success', text })
      await loadQuestions()
    } catch (err) {
      setBanner({ type: 'error', text: err.message || 'Vectorization failed.' })
    } finally {
      setVectorizing(false)
    }
  }

  const pendingCount = questions.filter((q) => !q.is_vectorized).length

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            Questions &amp; Vectorization
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {user?.company_name} · {user?.name} ({user?.type})
          </p>
        </div>
        <Button variant="secondary" onClick={logout}>
          Log out
        </Button>
      </div>

      {banner && (
        <div
          className={
            'mb-4 rounded-lg px-4 py-3 text-sm ' +
            (banner.type === 'success'
              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
              : 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400')
          }
        >
          {banner.text}
        </div>
      )}

      {/* Add question */}
      <Card className="mb-6">
        <CardHeader title="Add a question" subtitle="Create a Q&A pair for your company" />
        <CardBody>
          <form onSubmit={handleAdd} className="space-y-4">
            <Input
              label="Question"
              value={form.question}
              onChange={(e) => setForm((f) => ({ ...f, question: e.target.value }))}
              placeholder="What is your refund policy?"
            />
            <Textarea
              label="Answer"
              rows={3}
              value={form.answer}
              onChange={(e) => setForm((f) => ({ ...f, answer: e.target.value }))}
              placeholder="Refunds are processed within 7 business days."
            />
            <Button
              type="submit"
              loading={saving}
              disabled={!form.question.trim() || !form.answer.trim()}
            >
              Add question
            </Button>
          </form>
        </CardBody>
      </Card>

      {/* Questions list + vectorize */}
      <Card>
        <CardHeader
          title={`Questions (${questions.length})`}
          subtitle={`${pendingCount} pending vectorization`}
          action={
            <Button
              onClick={handleVectorize}
              loading={vectorizing}
              disabled={questions.length === 0}
            >
              Convert to vector
            </Button>
          }
        />
        <CardBody>
          {loading ? (
            <div className="flex justify-center py-10">
              <Spinner className="h-6 w-6" />
            </div>
          ) : questions.length === 0 ? (
            <EmptyState
              title="No questions yet"
              description="Add your first question above."
            />
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-800">
              {questions.map((q) => (
                <li key={q.id} className="flex items-start justify-between gap-4 py-3">
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 dark:text-gray-100">
                      {q.question}
                    </p>
                    <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
                      {q.answer}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <Badge tone={q.is_vectorized ? 'green' : 'gray'}>
                      {q.is_vectorized ? 'Vectorized' : 'Pending'}
                    </Badge>
                    <button
                      onClick={() => handleDelete(q.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
