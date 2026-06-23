import { cn } from '../../utils/cn'
import { formatTime } from '../../utils/format'
import Avatar from '../ui/Avatar'

/**
 * A single chat message. `sender` drives alignment & styling:
 *   customer -> left grey, ai -> left brand-tinted, agent -> right brand.
 */
export default function MessageBubble({ message }) {
  const sender = message.sender || 'customer'
  const isOutbound = sender === 'agent' || sender === 'ai'
  const isAgent = sender === 'agent'

  return (
    <div className={cn('flex items-end gap-2', isOutbound ? 'flex-row-reverse' : 'flex-row')}>
      {!isAgent && (
        <Avatar
          name={message.author || (sender === 'ai' ? 'AI' : 'Customer')}
          size="sm"
          className="mb-5"
        />
      )}
      <div className={cn('max-w-[78%] sm:max-w-[65%]', isOutbound && 'items-end')}>
        {message.author && (
          <p
            className={cn(
              'mb-1 text-xs text-gray-400',
              isOutbound ? 'text-right' : 'text-left',
            )}
          >
            {message.author}
          </p>
        )}
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm',
            isAgent && 'rounded-br-md bg-brand-600 text-white',
            sender === 'ai' &&
              'rounded-bl-md bg-violet-50 text-gray-800 ring-1 ring-violet-100 dark:bg-violet-500/10 dark:text-violet-100 dark:ring-violet-500/20',
            sender === 'customer' &&
              'rounded-bl-md bg-white text-gray-800 ring-1 ring-gray-200 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-700',
          )}
        >
          {message.body}
        </div>
        <p
          className={cn(
            'mt-1 text-[11px] text-gray-400',
            isOutbound ? 'text-right' : 'text-left',
          )}
        >
          {formatTime(message.created_at)}
        </p>
      </div>
    </div>
  )
}
