import { useEffect, useMemo } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  ChatBubbleLeftRightIcon,
  CpuChipIcon,
  UserGroupIcon,
  ArrowTrendingUpIcon,
  ExclamationTriangleIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { PageHeader, StatCard } from '../../components/ui'
import ChartCard from '../../components/charts/ChartCard'
import { ChartTooltip, axisProps, gridProps } from '../../components/charts/chartTheme'
import useAuth from '../../hooks/useAuth'
import {
  fetchOverview,
  fetchConversationsSeries,
  fetchTopFaqs,
} from '../../redux/slices/analyticsSlice'
import {
  mockOverview,
  mockDailySeries,
  mockWeeklySeries,
  mockTopFaqs,
} from '../../utils/mockData'

export default function DashboardPage() {
  const dispatch = useDispatch()
  const { user } = useAuth()
  const { overview, series, weeklySeries, topFaqs, status } = useSelector(
    (s) => s.analytics,
  )

  useEffect(() => {
    dispatch(fetchOverview())
    dispatch(fetchConversationsSeries({ granularity: 'day' }))
    dispatch(fetchConversationsSeries({ granularity: 'week' }))
    dispatch(fetchTopFaqs())
  }, [dispatch])

  // Fall back to demo data so the dashboard is presentable pre-integration.
  const data = overview || mockOverview
  const daily = series.length ? series : mockDailySeries
  const weekly = weeklySeries.length ? weeklySeries : mockWeeklySeries
  const faqs = topFaqs.length ? topFaqs : mockTopFaqs
  const loading = status === 'loading' && !overview

  const stats = useMemo(
    () => [
      { label: 'Total Conversations', value: data.total_conversations, icon: ChatBubbleLeftRightIcon, color: 'brand', delta: data.total_conversations_delta, gradient: true },
      { label: 'Resolved by AI', value: data.resolved_by_ai, icon: CpuChipIcon, color: 'green', delta: data.resolved_by_ai_delta },
      { label: 'Resolved by Agent', value: data.resolved_by_agent, icon: UserGroupIcon, color: 'blue', delta: data.resolved_by_agent_delta },
      { label: 'Escalated Chats', value: data.escalated, icon: ExclamationTriangleIcon, color: 'red', delta: data.escalated_delta },
      { label: 'Active Agents', value: data.active_agents, icon: ArrowTrendingUpIcon, color: 'amber' },
      { label: 'Unanswered Questions', value: data.unanswered, icon: QuestionMarkCircleIcon, color: 'slate' },
    ],
    [data],
  )

  const firstName = (user?.name || user?.full_name || 'there').split(' ')[0]

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${firstName} 👋`}
        subtitle="Here's what's happening across your support workspace today."
      />

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {stats.map((s) => (
          <StatCard key={s.label} loading={loading} {...s} />
        ))}
      </div>

      {/* Charts */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard
          title="Daily Conversations"
          subtitle="Conversations vs resolutions this week"
          className="lg:col-span-2"
        >
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={daily} margin={{ left: -16, right: 8, top: 8 }}>
              <defs>
                <linearGradient id="gConv" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gRes" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="label" {...axisProps} />
              <YAxis {...axisProps} />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey="conversations" stroke="#6366f1" strokeWidth={2.5} fill="url(#gConv)" />
              <Area type="monotone" dataKey="resolved" stroke="#10b981" strokeWidth={2.5} fill="url(#gRes)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Weekly Conversations" subtitle="Last 4 weeks">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={weekly} margin={{ left: -16, right: 8, top: 8 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="label" {...axisProps} />
              <YAxis {...axisProps} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(99,102,241,0.06)' }} />
              <Bar dataKey="conversations" fill="#6366f1" radius={[6, 6, 0, 0]} maxBarSize={42} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Top FAQs */}
      <div className="mt-6">
        <ChartCard title="Top FAQs" subtitle="Most frequently asked questions">
          <div className="space-y-3">
            {faqs.map((faq, i) => {
              const max = faqs[0]?.count || 1
              const pct = Math.round((faq.count / max) * 100)
              return (
                <div key={faq.question} className="flex items-center gap-4">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-xs font-semibold text-brand-700 dark:bg-brand-500/10 dark:text-brand-300">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-medium text-gray-700 dark:text-gray-200">
                        {faq.question}
                      </p>
                      <span className="shrink-0 text-sm font-semibold text-gray-500 dark:text-gray-400">
                        {faq.count}
                      </span>
                    </div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-brand-500 to-violet-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </ChartCard>
      </div>
    </div>
  )
}
