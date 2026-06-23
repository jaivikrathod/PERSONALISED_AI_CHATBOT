import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import TypingIndicator from './TypingIndicator'
import Spinner from '../ui/Spinner'

/**
 * Scrollable message list with:
 *  - auto-scroll to bottom on new messages (unless user scrolled up)
 *  - "Load more" at the top for older history
 *  - typing indicator pinned to the bottom
 */
export default function MessageThread({
  messages = [],
  loading = false,
  hasMore = false,
  onLoadMore,
  isPeerTyping = false,
  typingName,
}) {
  const bottomRef = useRef(null)
  const containerRef = useRef(null)
  const stickToBottom = useRef(true)

  // Track whether the user is near the bottom so we don't yank them down.
  const onScroll = () => {
    const el = containerRef.current
    if (!el) return
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120
  }

  useEffect(() => {
    if (stickToBottom.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages.length, isPeerTyping])

  return (
    <div
      ref={containerRef}
      onScroll={onScroll}
      className="flex-1 space-y-4 overflow-y-auto bg-gray-50 px-4 py-5 dark:bg-gray-950 sm:px-6"
    >
      {hasMore && (
        <div className="flex justify-center">
          <button
            onClick={onLoadMore}
            className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-500 shadow-sm transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
          >
            Load earlier messages
          </button>
        </div>
      )}

      {loading && messages.length === 0 ? (
        <div className="flex h-full items-center justify-center text-brand-600">
          <Spinner className="h-7 w-7" />
        </div>
      ) : (
        messages.map((m) => <MessageBubble key={m.id} message={m} />)
      )}

      {isPeerTyping && <TypingIndicator name={typingName} />}
      <div ref={bottomRef} />
    </div>
  )
}
