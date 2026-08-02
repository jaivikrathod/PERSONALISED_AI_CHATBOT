import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import DashboardLayout from '../components/layout/DashboardLayout'
import ProtectedRoute from './ProtectedRoute'
import PublicRoute from './PublicRoute'
import RoleRoute from './RoleRoute'
import Spinner from '../components/ui/Spinner'
import { MANAGER_TYPES, USER_TYPES } from '../utils/constants'

// Code-split pages so the initial bundle stays light.
const RegisterPage = lazy(() => import('../pages/auth/RegisterPage'))
const LoginPage = lazy(() => import('../pages/auth/LoginPage'))
const KnowledgeBasePage = lazy(
  () => import('../pages/knowledge-base/KnowledgeBasePage'),
)
const UnansweredPage = lazy(() => import('../pages/unanswered/UnansweredPage'))
const UsersPage = lazy(() => import('../pages/users/UsersPage'))
const ChatbotPage = lazy(() => import('../pages/chatbot/ChatbotPage'))
const AgentConsolePage = lazy(() => import('../pages/agents/AgentConsolePage'))
const NotFoundPage = lazy(() => import('../pages/NotFoundPage'))

function PageFallback() {
  return (
    <div className="flex h-[60vh] items-center justify-center text-brand-600">
      <Spinner className="h-8 w-8" />
    </div>
  )
}

export default function AppRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        {/* Public — registration is the start of the flow. */}
        <Route element={<PublicRoute />}>
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<LoginPage />} />
        </Route>

        {/* Protected app shell */}
        <Route element={<ProtectedRoute />}>
          <Route element={<DashboardLayout />}>
            {/* Admin / Manager area */}
            <Route
              element={
                <RoleRoute
                  allow={MANAGER_TYPES}
                  description="Only Admin and Manager users can access this area."
                />
              }
            >
              <Route path="/manage_questions" element={<KnowledgeBasePage />} />
              <Route path="/unanswered" element={<UnansweredPage />} />
              <Route path="/users" element={<UsersPage />} />
            </Route>

            {/* Agent console */}
            <Route
              element={
                <RoleRoute
                  allow={[USER_TYPES.AGENT]}
                  description="This page is only available to users of type Agent."
                />
              }
            >
              <Route path="/agent" element={<AgentConsolePage />} />
            </Route>

            <Route path="/chatbot" element={<ChatbotPage />} />
          </Route>
        </Route>

        {/* Default + unknown routes */}
        <Route path="/" element={<Navigate to="/register" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
