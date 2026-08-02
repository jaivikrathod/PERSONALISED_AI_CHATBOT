import Avatar from '../ui/Avatar'
import { cn } from '../../utils/cn'
import { formatTime } from '../../utils/format'

/**
 * A single chat bubble. `tone` picks the palette and `outbound` the side, so
 * the same component serves the customer widget and the agent console:
 *   neutral -> white (incoming), ai -> violet, brand -> the current user,
 *   human   -> a live support agent, error -> failed/rejected message.
 * `tone="system"` renders a centered notice instead of a bubble.
 */
const TONES = {
  neutral:
    'bg-white text-gray-800 ring-1 ring-gray-200 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-700',
  ai: 'bg-violet-50 text-gray-800 ring-1 ring-violet-100 dark:bg-violet-500/10 dark:text-violet-100 dark:ring-violet-500/20',
  brand: 'bg-brand-600 text-white',
  human:
    'bg-emerald-50 text-emerald-900 ring-1 ring-emerald-100 dark:bg-emerald-500/10 dark:text-emerald-200 dark:ring-emerald-500/20',
  error:
    'bg-red-50 text-red-700 ring-1 ring-red-100 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20',
}

export default function MessageBubble({
  tone = 'neutral',
  author,
  body,
  createdAt,
  outbound = false,
}) {
  if (tone === 'system') {
    return (
      <div className="flex justify-center">
        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-500 dark:bg-gray-800 dark:text-gray-400">
          {body}
        </span>
      </div>
    )
  }

  return (
    <div className={cn('flex items-end gap-2', outbound ? 'flex-row-reverse' : 'flex-row')}>
      {!outbound && <Avatar name={author || 'Customer'} size="sm" className="mb-5" />}
      <div className="max-w-[80%] sm:max-w-[68%]">
        {author && (
          <p
            className={cn(
              'mb-1 text-xs text-gray-400',
              outbound ? 'text-right' : 'text-left',
            )}
          >
            {author}
          </p>
        )}
        <div
          className={cn(
            'whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm',
            outbound ? 'rounded-br-md' : 'rounded-bl-md',
            TONES[tone] || TONES.neutral,
          )}
        >
          {body}
        </div>
        {createdAt && (
          <p
            className={cn(
              'mt-1 text-[11px] text-gray-400',
              outbound ? 'text-right' : 'text-left',
            )}
          >
            {formatTime(createdAt)}
          </p>
        )}
      </div>
    </div>
  )
}
