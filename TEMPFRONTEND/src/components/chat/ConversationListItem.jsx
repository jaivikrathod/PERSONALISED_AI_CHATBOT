import Badge from '../ui/Badge'
import Avatar from '../ui/Avatar'
import { cn } from '../../utils/cn'
import { timeAgo, truncate } from '../../utils/format'
import { SESSION_STATUS_LABEL, SESSION_STATUS_TONE } from '../../utils/constants'

/**
 * One row in a conversation sidebar. Shared by the customer widget (session
 * history) and the agent console (assigned chats).
 */
export default function ConversationListItem({
  title,
  preview,
  status,
  meta,
  updatedAt,
  unread = false,
  active = false,
  onClick,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? 'true' : undefined}
      className={cn(
        'flex w-full gap-3 border-l-2 px-4 py-3 text-left transition-colors',
        active
          ? 'border-brand-600 bg-brand-50/60 dark:bg-brand-500/10'
          : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50',
      )}
    >
      <Avatar name={title} size="md" status={unread ? 'online' : undefined} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p
            className={cn(
              'truncate text-sm',
              unread
                ? 'font-semibold text-gray-900 dark:text-gray-100'
                : 'font-medium text-gray-700 dark:text-gray-300',
            )}
          >
            {title}
          </p>
          {updatedAt && (
            <span className="shrink-0 text-[11px] text-gray-400">
              {timeAgo(updatedAt)}
            </span>
          )}
        </div>
        <div className="mt-0.5 flex items-center justify-between gap-2">
          <p
            className={cn(
              'truncate text-xs',
              unread ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400',
            )}
          >
            {truncate(preview, 40) || 'No messages yet.'}
          </p>
          {status ? (
            <Badge
              tone={SESSION_STATUS_TONE[status] || 'gray'}
              className="shrink-0 !px-1.5 !py-0 !text-[10px] normal-case"
            >
              {SESSION_STATUS_LABEL[status] || status}
            </Badge>
          ) : (
            meta && <span className="shrink-0 text-[11px] text-gray-400">{meta}</span>
          )}
        </div>
      </div>
    </button>
  )
}
