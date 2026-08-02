import { useEffect, useRef } from 'react'
import Spinner from '../ui/Spinner'
import EmptyState from '../ui/EmptyState'
import TypingIndicator from './TypingIndicator'

/**
 * Scrollable message list.
 *  - auto-scrolls to the bottom on new messages, unless the user scrolled up
 *  - renders loading / empty states in place
 *  - pins a typing indicator to the bottom while a reply is pending
 */
export default function MessageThread({
  children,
  loading = false,
  isEmpty = false,
  emptyIcon,
  emptyTitle,
  emptyDescription,
  pending = false,
  pendingLabel,
  pendingName,
  scrollKey,
}) {
  const containerRef = useRef(null)
  const bottomRef = useRef(null)
  const stickToBottom = useRef(true)

  // Track whether the user is near the bottom so we don't yank them down.
  const onScroll = () => {
    const el = containerRef.current
    if (!el) return
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120
  }

  useEffect(() => {
    if (stickToBottom.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [scrollKey, pending, loading])

  return (
    <div
      ref={containerRef}
      onScroll={onScroll}
      className="flex-1 space-y-4 overflow-y-auto bg-gray-50 px-4 py-5 dark:bg-gray-950 sm:px-6"
    >
      {loading ? (
        <div className="flex h-full items-center justify-center text-brand-600">
          <Spinner className="h-7 w-7" />
        </div>
      ) : isEmpty ? (
        <div className="flex h-full items-center justify-center">
          <EmptyState
            icon={emptyIcon}
            title={emptyTitle}
            description={emptyDescription}
          />
        </div>
      ) : (
        children
      )}

      {pending && <TypingIndicator name={pendingName} label={pendingLabel} />}
      <div ref={bottomRef} />
    </div>
  )
}
