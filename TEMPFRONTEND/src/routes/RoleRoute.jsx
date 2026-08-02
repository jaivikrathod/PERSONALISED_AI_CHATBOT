import { Outlet } from 'react-router-dom'
import { LockClosedIcon } from '@heroicons/react/24/outline'
import { Card, CardBody, EmptyState } from '../components/ui'
import useAuth from '../hooks/useAuth'

/**
 * Restricts a branch of the app to specific `users.User.type` values.
 * Renders an in-shell "access denied" state rather than redirecting, so the
 * user keeps their navigation context (same behaviour the pages had inline).
 */
export default function RoleRoute({ allow = [], description }) {
  const { userType } = useAuth()
  if (allow.includes(userType)) return <Outlet />

  return (
    <Card>
      <CardBody className="py-10">
        <EmptyState
          icon={LockClosedIcon}
          title="Access denied"
          description={description || 'You do not have permission to view this page.'}
        />
      </CardBody>
    </Card>
  )
}
