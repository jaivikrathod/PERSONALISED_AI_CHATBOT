import { BellIcon } from '@heroicons/react/24/outline'
import {
  ChatBubbleLeftRightIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/solid'
import Dropdown from '../ui/Dropdown'
import { cn } from '../../utils/cn'

// Demo notifications — replace with a notifications slice/endpoint.
const DEMO = [
  {
    id: 1,
    icon: ExclamationTriangleIcon,
    tone: 'text-amber-500',
    title: 'Chat escalated to a human agent',
    time: '2m ago',
    unread: true,
  },
  {
    id: 2,
    icon: ChatBubbleLeftRightIcon,
    tone: 'text-brand-500',
    title: 'New conversation from widget',
    time: '15m ago',
    unread: true,
  },
  {
    id: 3,
    icon: CheckCircleIcon,
    tone: 'text-emerald-500',
    title: 'AI resolved 12 conversations today',
    time: '1h ago',
    unread: false,
  },
]

export default function NotificationsDropdown() {
  const unread = DEMO.filter((n) => n.unread).length

  return (
    <Dropdown
      width="w-80"
      trigger={
        <button className="relative rounded-lg p-2 text-gray-500 transition hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800">
          <BellIcon className="h-5 w-5" />
          {unread > 0 && (
            <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
              {unread}
            </span>
          )}
        </button>
      }
    >
      <div className="flex items-center justify-between px-4 py-3">
        <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">
          Notifications
        </p>
        <button className="text-xs font-medium text-brand-600 hover:underline">
          Mark all read
        </button>
      </div>
      <div className="max-h-80 overflow-y-auto border-t border-gray-100 dark:border-gray-800">
        {DEMO.map((n) => (
          <div
            key={n.id}
            className={cn(
              'flex gap-3 px-4 py-3 transition hover:bg-gray-50 dark:hover:bg-gray-800/60',
              n.unread && 'bg-brand-50/40 dark:bg-brand-500/5',
            )}
          >
            <n.icon className={cn('mt-0.5 h-5 w-5 shrink-0', n.tone)} />
            <div className="min-w-0">
              <p className="text-sm text-gray-700 dark:text-gray-200">{n.title}</p>
              <p className="mt-0.5 text-xs text-gray-400">{n.time}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="border-t border-gray-100 px-4 py-2.5 text-center dark:border-gray-800">
        <button className="text-xs font-medium text-brand-600 hover:underline">
          View all notifications
        </button>
      </div>
    </Dropdown>
  )
}
