import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useDispatch } from 'react-redux'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  CheckCircleIcon,
  EnvelopeIcon,
  LockClosedIcon,
} from '@heroicons/react/24/outline'
import { Button, Input } from '../../components/ui'
import AuthLayout from './AuthLayout'
import useAuth from '../../hooks/useAuth'
import { clearAuthError, login } from '../../redux/slices/authSlice'
import { homePathForType } from '../../routes/navigation'

/**
 * Entry point: log in with the credentials created at registration.
 * Agents land in the support console, everyone else in the admin app.
 */
export default function LoginPage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const { isLoading, error } = useAuth()

  const justRegistered = location.state?.registered

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: { email: location.state?.email || '', password: '' },
  })

  useEffect(() => () => dispatch(clearAuthError()), [dispatch])

  const onSubmit = async (values) => {
    const result = await dispatch(login(values))
    if (login.fulfilled.match(result)) {
      navigate(homePathForType(result.payload?.type), { replace: true })
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to your questions and vectorization tools."
    >
      {justRegistered && (
        <div className="mt-5 flex items-start gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-400">
          <CheckCircleIcon className="h-5 w-5 shrink-0" />
          <span>Account created — please log in.</span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400"
        >
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

        <Input
          label="Password"
          type="password"
          placeholder="••••••••"
          icon={<LockClosedIcon className="h-5 w-5" />}
          autoComplete="current-password"
          error={errors.password?.message}
          {...register('password', { required: 'Password is required' })}
        />

        <Button type="submit" size="lg" className="w-full" loading={isLoading}>
          Log in
        </Button>
      </form>

      <p className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
        No account?{' '}
        <Link to="/register" className="font-medium text-brand-600 hover:underline">
          Register a company
        </Link>
      </p>
    </AuthLayout>
  )
}
