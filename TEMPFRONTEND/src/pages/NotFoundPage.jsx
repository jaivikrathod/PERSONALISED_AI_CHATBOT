import { Link } from 'react-router-dom'
import { Button } from '../components/ui'
import useAuth from '../hooks/useAuth'
import { homePathForType } from '../routes/navigation'

export default function NotFoundPage() {
  const { isAuthenticated, userType } = useAuth()
  const to = isAuthenticated ? homePathForType(userType) : '/login'

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-6 text-center dark:bg-gray-950">
      <p className="text-7xl font-bold text-brand-600">404</p>
      <h1 className="mt-4 text-2xl font-bold text-gray-900 dark:text-white">
        Page not found
      </h1>
      <p className="mt-2 max-w-sm text-sm text-gray-500 dark:text-gray-400">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Button as={Link} to={to} className="mt-6">
        {isAuthenticated ? 'Back to the app' : 'Go to login'}
      </Button>
    </div>
  )
}
