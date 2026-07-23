import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import DashboardLayout from '../components/layout/DashboardLayout'
import ProtectedRoute from './ProtectedRoute'
import PublicRoute from './PublicRoute'
import Spinner from '../components/ui/Spinner'

// Code-split pages so the initial bundle stays light.
const LoginPage = lazy(() => import('../pages/auth/LoginPage'))
const DashboardPage = lazy(() => import('../pages/dashboard/DashboardPage'))
const KnowledgeBasePage = lazy(() => import('../pages/knowledge-base/KnowledgeBasePage'))
const ChatbotsPage = lazy(() => import('../pages/chatbots/ChatbotsPage'))
const ConversationsPage = lazy(() => import('../pages/conversations/ConversationsPage'))
const AgentChatPage = lazy(() => import('../pages/agents/AgentChatPage'))
const AnalyticsPage = lazy(() => import('../pages/analytics/AnalyticsPage'))
const UnansweredPage = lazy(() => import('../pages/unanswered/UnansweredPage'))
const SettingsPage = lazy(() => import('../pages/settings/SettingsPage'))
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
        {/* Public */}
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>

        {/* Protected app shell */}
        <Route element={<PublicRoute />}>
          <Route element={<DashboardLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/knowledge-base" element={<KnowledgeBasePage />} />
            <Route path="/chatbots" element={<ChatbotsPage />} />
            <Route path="/conversations" element={<ConversationsPage />} />
            <Route path="/agents" element={<AgentChatPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/unanswered" element={<UnansweredPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
