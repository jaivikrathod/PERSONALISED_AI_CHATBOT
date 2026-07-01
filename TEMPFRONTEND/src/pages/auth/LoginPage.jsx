import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useDispatch } from 'react-redux'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import {
  EnvelopeIcon,
  LockClosedIcon,
  SparklesIcon,
  ShieldCheckIcon,
  BoltIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import { Button, Input } from '../../components/ui'
import useAuth from '../../hooks/useAuth'
import { clearAuthError, login } from '../../redux/slices/authSlice'

export default function LoginPage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const { isLoading, error } = useAuth()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ defaultValues: { email: '', password: '' } })

  useEffect(() => () => dispatch(clearAuthError()), [dispatch])

  const onSubmit = async (values) => {
    const result = await dispatch(login(values))
    if (login.fulfilled.match(result)) {
      const to = location.state?.from?.pathname || '/dashboard'
      navigate(to, { replace: true })
    }
  }

  return (
    <div className="flex min-h-screen bg-white dark:bg-gray-950">
      {/* Left — form */}
      <div className="flex w-full flex-col justify-center px-6 py-12 sm:px-12 lg:w-1/2 xl:px-24">
        <div className="mx-auto w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 text-white shadow-sm">
              <SparklesIcon className="h-6 w-6" />
            </span>
            <span className="text-xl font-bold tracking-tight text-gray-900 dark:text-white">
              SupportAI
            </span>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Welcome back
          </h1>
          <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">
            Sign in to your customer support workspace.
          </p>

          {error && (
            <div className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4" noValidate>
            <Input
              label="Email address"
              type="email"
              placeholder="you@company.com"
              icon={<EnvelopeIcon className="h-5 w-5" />}
              autoComplete="email"
              error={errors.email?.message}
              {...register('email', {
                required: 'Email is required',
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: 'Enter a valid email address',
                },
              })}
            />

            <div>
              <Input
                label="Password"
                type="password"
                placeholder="••••••••"
                icon={<LockClosedIcon className="h-5 w-5" />}
                autoComplete="current-password"
                error={errors.password?.message}
                {...register('password', {
                  required: 'Password is required',
                  minLength: { value: 6, message: 'At least 6 characters' },
                })}
              />
              <div className="mt-1.5 text-right">
                <Link to="#" className="text-xs font-medium text-brand-600 hover:underline">
                  Forgot password?
                </Link>
              </div>
            </div>

            <Button type="submit" className="w-full" size="lg" loading={isLoading}>
              Sign in
            </Button>
          </form>

          <p className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
            Don&apos;t have an account?{' '}
            <Link to="#" className="font-medium text-brand-600 hover:underline">
              Contact sales
            </Link>
          </p>
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
            Resolve conversations faster with AI, seamless agent handoff, and
            actionable analytics — all in one platform.
          </p>
          <ul className="mt-10 space-y-5">
            {[
              { icon: BoltIcon, t: 'Instant AI resolutions', d: 'Answer FAQs 24/7 from your knowledge base.' },
              { icon: ShieldCheckIcon, t: 'Smart escalation', d: 'Hand off to live agents when it matters.' },
              { icon: ChartBarIcon, t: 'Deep analytics', d: 'Track resolution rates and gaps in real time.' },
            ].map(({ icon: Icon, t, d }) => (
              <li key={t} className="flex gap-3.5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/15 backdrop-blur">
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <p className="font-semibold">{t}</p>
                  <p className="text-sm text-white/70">{d}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
