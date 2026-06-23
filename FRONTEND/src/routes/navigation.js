import {
  Squares2X2Icon,
  BookOpenIcon,
  CpuChipIcon,
  ChatBubbleLeftRightIcon,
  UserGroupIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline'

// Single source of truth for sidebar + breadcrumb labels.
export const NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard', icon: Squares2X2Icon },
  { label: 'Knowledge Base', to: '/knowledge-base', icon: BookOpenIcon },
  { label: 'Chatbots', to: '/chatbots', icon: CpuChipIcon },
  { label: 'Conversations', to: '/conversations', icon: ChatBubbleLeftRightIcon },
  { label: 'Agents', to: '/agents', icon: UserGroupIcon },
  {
    label: 'Unanswered',
    to: '/unanswered',
    icon: QuestionMarkCircleIcon,
  },
  { label: 'Analytics', to: '/analytics', icon: ChartBarIcon },
  { label: 'Settings', to: '/settings', icon: Cog6ToothIcon },
]

// Map first path segment -> human label for breadcrumbs.
export const ROUTE_LABELS = NAV_ITEMS.reduce((acc, item) => {
  acc[item.to.replace('/', '')] = item.label
  return acc
}, {})
