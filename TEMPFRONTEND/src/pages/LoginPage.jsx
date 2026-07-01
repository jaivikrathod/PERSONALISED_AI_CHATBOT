import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Button, Input, Card, CardBody } from '../components/ui'
import { authService } from '../services/authService'
import { useAuth } from '../context/AuthContext'

/**
 * Step 2 (entry): log in with the Admin credentials created at registration.
 * On success the user is stored and we go to the dashboard.
 */
export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const [serverError, setServerError] = useState('')

  const justRegistered = location.state?.registered
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: { email: location.state?.email || '' },
  })

  const onSubmit = async (values) => {
    setServerError('')
    try {
      const user = await authService.login(values)
      login(user)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setServerError(err.message || 'Login failed.')
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4">
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Log in</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Access your questions and vectorization tools.
        </p>
      </div>

      <Card>
        <CardBody>
          {justRegistered && (
            <div className="mb-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">
              Account created — please log in.
            </div>
          )}
          {serverError && (
            <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
              {serverError}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Email"
              type="email"
              error={errors.email?.message}
              {...register('email', { required: 'Required' })}
            />
            <Input
              label="Password"
              type="password"
              error={errors.password?.message}
              {...register('password', { required: 'Required' })}
            />
            <Button type="submit" size="lg" loading={isSubmitting} className="w-full">
              Log in
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
            No account?{' '}
            <Link to="/register" className="font-medium text-brand-600 hover:underline">
              Register a company
            </Link>
          </p>
        </CardBody>
      </Card>
    </div>
  )
}
