import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  ChatBubbleLeftRightIcon,
  ExclamationTriangleIcon,
  CpuChipIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { PageHeader, StatCard, Select } from '../../components/ui'
import ChartCard from '../../components/charts/ChartCard'
import {
  ChartTooltip,
  axisProps,
  gridProps,
  CHART_COLORS,
} from '../../components/charts/chartTheme'
import {
  fetchOverview,
  fetchConversationsSeries,
  fetchTopFaqs,
} from '../../redux/slices/analyticsSlice'
import {
  mockOverview,
  mockDailySeries,
  mockTopFaqs,
} from '../../utils/mockData'

const RANGE_OPTIONS = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 90 days' },
]

function isoDaysAgo(days) {
  const d = new Date()
  d.setDate(d.getDate() - Number(days))
  return d.toISOString().slice(0, 10)
}

export default function AnalyticsPage() {
  const dispatch = useDispatch()
  const { overview, series, topFaqs } = useSelector((s) => s.analytics)
  const [range, setRange] = useState('30')

  useEffect(() => {
    const params = { from: isoDaysAgo(range), to: isoDaysAgo(0) }
    dispatch(fetchOverview(params))
    dispatch(fetchConversationsSeries({ ...params, granularity: 'day' }))
    dispatch(fetchTopFaqs())
  }, [dispatch, range])

  const data = overview || mockOverview
  const lineData = series.length ? series : mockDailySeries
  const faqs = topFaqs.length ? topFaqs : mockTopFaqs

  const aiPct = Math.round(
    (data.resolved_by_ai / (data.resolved_by_ai + data.resolved_by_agent || 1)) * 100,
  )
  const agentPct = 100 - aiPct

  const resolutionData = [
    { name: 'Resolved by AI', value: data.resolved_by_ai },
    { name: 'Resolved by Agent', value: data.resolved_by_agent },
    { name: 'Escalated', value: data.escalated },
  ]

  const stats = [
    { label: 'Total Conversations', value: data.total_conversations, icon: ChatBubbleLeftRightIcon, color: 'brand', gradient: true, delta: data.total_conversations_delta },
    { label: 'Escalations', value: data.escalated, icon: ExclamationTriangleIcon, color: 'red', delta: data.escalated_delta },
    { label: 'AI Resolution %', value: aiPct, icon: CpuChipIcon, color: 'green' },
    { label: 'Agent Resolution %', value: agentPct, icon: UserGroupIcon, color: 'blue' },
  ]

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Measure resolution performance and spot gaps.">
        <Select
          value={range}
          onChange={(e) => setRange(e.target.value)}
          options={RANGE_OPTIONS}
          containerClassName="w-44"
        />
      </PageHeader>

      {/* Overview cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((s) => (
          <StatCard key={s.label} {...s} />
        ))}
      </div>

      {/* Line + Pie */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard title="Conversations Over Time" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={lineData} margin={{ left: -16, right: 8, top: 8 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="label" {...axisProps} />
              <YAxis {...axisProps} />
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="conversations" stroke="#6366f1" strokeWidth={2.5} dot={false} />
              <Line type="monotone" dataKey="resolved" stroke="#10b981" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Resolution Breakdown">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={resolutionData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="45%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={3}
              >
                {resolutionData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i]} />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Top questions bar + Unanswered link card */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard title="Top Questions" subtitle="Most asked, by volume">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={faqs}
              layout="vertical"
              margin={{ left: 8, right: 16, top: 8 }}
            >
              <CartesianGrid {...gridProps} horizontal={false} />
              <XAxis type="number" {...axisProps} />
              <YAxis
                type="category"
                dataKey="question"
                width={150}
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickFormatter={(v) => (v.length > 22 ? `${v.slice(0, 22)}…` : v)}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(99,102,241,0.06)' }} />
              <Bar dataKey="count" fill="#8b5cf6" radius={[0, 6, 6, 0]} maxBarSize={26} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="AI vs Agent Resolutions" subtitle="Daily comparison">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={lineData} margin={{ left: -16, right: 8, top: 8 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="label" {...axisProps} />
              <YAxis {...axisProps} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(99,102,241,0.06)' }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="resolved" name="Resolved" fill="#10b981" radius={[6, 6, 0, 0]} maxBarSize={28} />
              <Bar dataKey="conversations" name="Total" fill="#6366f1" radius={[6, 6, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}
