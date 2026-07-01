import Avatar from '../ui/Avatar'
import Badge, { STATUS_TONE } from '../ui/Badge'
import { cn } from '../../utils/cn'
import { timeAgo, truncate } from '../../utils/format'

export default function ConversationListItem({ conversation, active, onClick }) {
  const { customer_name, last_message, status, unread_count, updated_at } = conversation
  const hasUnread = unread_count > 0

  return (
    <button
      onClick={onClick}
      className={cn(
        'flex w-full gap-3 border-l-2 px-4 py-3 text-left transition-colors',
        active
          ? 'border-brand-600 bg-brand-50/60 dark:bg-brand-500/10'
          : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50',
      )}
    >
      <Avatar name={customer_name} size="md" status={hasUnread ? 'online' : undefined} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p
            className={cn(
              'truncate text-sm',
              hasUnread
                ? 'font-semibold text-gray-900 dark:text-gray-100'
                : 'font-medium text-gray-700 dark:text-gray-300',
            )}
          >
            {customer_name}
          </p>
          <span className="shrink-0 text-[11px] text-gray-400">{timeAgo(updated_at)}</span>
        </div>
        <div className="mt-0.5 flex items-center justify-between gap-2">
          <p
            className={cn(
              'truncate text-xs',
              hasUnread ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400',
            )}
          >
            {truncate(last_message, 38)}
          </p>
          {hasUnread ? (
            <span className="flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-brand-600 px-1.5 text-[10px] font-bold text-white">
              {unread_count}
            </span>
          ) : (
            <Badge tone={STATUS_TONE[status]} className="shrink-0 !px-1.5 !py-0 !text-[10px]">
              {status}
            </Badge>
          )}
        </div>
      </div>
    </button>
  )
}
