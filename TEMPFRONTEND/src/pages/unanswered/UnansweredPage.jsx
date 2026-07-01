import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { QuestionMarkCircleIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { PageHeader, Table, Button, Badge } from '../../components/ui'
import ConvertToFaqModal from './ConvertToFaqModal'
import { timeAgo } from '../../utils/format'
import { fetchUnanswered } from '../../redux/slices/analyticsSlice'
import { mockUnanswered } from '../../utils/mockData'

export default function UnansweredPage() {
  const dispatch = useDispatch()
  const { unanswered, status } = useSelector((s) => s.analytics)
  const [converting, setConverting] = useState(null)

  useEffect(() => {
    dispatch(fetchUnanswered())
  }, [dispatch])

  const usingMock = status !== 'loading' && unanswered.length === 0
  const rows = usingMock ? mockUnanswered : unanswered

  const columns = [
    {
      key: 'question',
      header: 'Question',
      className: 'font-medium text-gray-900 dark:text-gray-100 max-w-md',
      render: (r) => <span className="line-clamp-1">{r.question}</span>,
    },
    {
      key: 'count',
      header: 'Times Asked',
      render: (r) => (
        <Badge tone={r.count > 20 ? 'red' : r.count > 10 ? 'yellow' : 'gray'}>
          {r.count}×
        </Badge>
      ),
    },
    {
      key: 'last_asked',
      header: 'Last Asked',
      render: (r) => <span className="text-gray-500">{timeAgo(r.last_asked)}</span>,
    },
    {
      key: 'actions',
      header: '',
      headerClassName: 'text-right',
      className: 'text-right',
      render: (r) => (
        <Button size="sm" variant="subtle" onClick={() => setConverting(r)}>
          <SparklesIcon className="h-4 w-4" />
          Convert to FAQ
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Unanswered Questions"
        subtitle="Questions your AI couldn't answer — turn them into FAQs to close the gap."
      />

      <Table
        columns={columns}
        data={rows}
        loading={status === 'loading'}
        emptyTitle="No unanswered questions"
        emptyDescription="Your knowledge base is covering everything customers ask. 🎉"
        emptyIcon={QuestionMarkCircleIcon}
      />

      <ConvertToFaqModal
        open={Boolean(converting)}
        onClose={() => setConverting(null)}
        question={converting}
      />
    </div>
  )
}
