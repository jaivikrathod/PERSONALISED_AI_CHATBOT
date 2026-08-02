import {
  BookOpenIcon,
  ChatBubbleLeftRightIcon,
  QuestionMarkCircleIcon,
  UserGroupIcon,
  UsersIcon,
} from '@heroicons/react/24/outline'
import { MANAGER_TYPES, USER_TYPES } from '../utils/constants'

/**
 * Single source of truth for the sidebar and the breadcrumb labels.
 * `roles` mirrors what each page already enforced: user management is
 * Admin/Manager only and the agent console is Agent only.
 */
export const NAV_ITEMS = [
  {
    label: 'Knowledge Base',
    to: '/manage_questions',
    icon: BookOpenIcon,
    roles: MANAGER_TYPES,
  },
  {
    label: 'Unanswered',
    to: '/unanswered',
    icon: QuestionMarkCircleIcon,
    roles: MANAGER_TYPES,
    badge: 'unanswered',
  },
  {
    label: 'Users',
    to: '/users',
    icon: UsersIcon,
    roles: MANAGER_TYPES,
  },
  {
    label: 'Agent Console',
    to: '/agent',
    icon: UserGroupIcon,
    roles: [USER_TYPES.AGENT],
  },
  {
    label: 'Chatbot',
    to: '/chatbot',
    icon: ChatBubbleLeftRightIcon,
  },
]

/** Nav entries visible to a given user type (no `roles` = everyone). */
export const navItemsForType = (userType) =>
  NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(userType))

/** Landing page per user type — Agents live in the console, everyone else in the admin app. */
export const homePathForType = (userType) =>
  userType === USER_TYPES.AGENT ? '/agent' : '/manage_questions'

// Map first path segment -> human label for breadcrumbs.
export const ROUTE_LABELS = NAV_ITEMS.reduce((acc, item) => {
  acc[item.to.replace('/', '')] = item.label
  return acc
}, {})
