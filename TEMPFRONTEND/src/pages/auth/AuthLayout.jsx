import { Link } from 'react-router-dom'
import {
  BoltIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import ThemeToggle from '../../components/layout/ThemeToggle'
import { cn } from '../../utils/cn'

const HIGHLIGHTS = [
  {
    icon: BoltIcon,
    title: 'Instant AI answers',
    description: 'Your FAQ knowledge base, vectorized and searchable 24/7.',
  },
  {
    icon: ShieldCheckIcon,
    title: 'Smart escalation',
    description: 'Unanswered questions hand off to a free agent automatically.',
  },
  {
    icon: ChartBarIcon,
    title: 'Close the gaps',
    description: 'Answer once — it is vectorized and reused straight away.',
  },
]

/**
 * Split-screen shell shared by the login and registration screens: form on
 * the left, brand panel on the right (hidden below `lg`).
 */
export default function AuthLayout({ title, subtitle, width = 'max-w-sm', children }) {
  return (
    <div className="flex min-h-screen bg-white dark:bg-gray-950">
      {/* Left — form */}
      <div className="flex w-full flex-col justify-center px-6 py-12 sm:px-12 lg:w-1/2 xl:px-24">
        <div className={cn('mx-auto w-full', width)}>
          <div className="mb-8 flex items-center justify-between gap-3">
            <Link to="/login" className="flex items-center gap-2.5">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 text-white shadow-sm">
                <SparklesIcon className="h-6 w-6" />
              </span>
              <span className="text-xl font-bold tracking-tight text-gray-900 dark:text-white">
                SupportAI
              </span>
            </Link>
            <ThemeToggle />
          </div>

          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{title}</h1>
          {subtitle && (
            <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>
          )}

          {children}
        </div>
      </div>

      {/* Right — brand panel */}
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-brand-600 via-violet-600 to-indigo-700 lg:flex lg:w-1/2 lg:flex-col lg:justify-center lg:px-16">
        <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-white/10 blur-2xl" />
        <div className="absolute -bottom-24 -left-10 h-72 w-72 rounded-full bg-white/10 blur-2xl" />
        <div className="relative z-10 max-w-md text-white">
          <h2 className="text-3xl font-bold leading-tight">
            AI-powered customer support, on autopilot.
          </h2>
          <p className="mt-4 text-white/80">
            Turn your FAQs into vector embeddings, answer customers instantly, and
            escalate to a human the moment the AI is unsure.
          </p>
          <ul className="mt-10 space-y-5">
            {HIGHLIGHTS.map(({ icon: Icon, title: t, description }) => (
              <li key={t} className="flex gap-3.5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/15 backdrop-blur">
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <p className="font-semibold">{t}</p>
                  <p className="text-sm text-white/70">{description}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
