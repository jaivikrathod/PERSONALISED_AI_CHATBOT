import { useRef, useState } from 'react'
import { PaperAirplaneIcon } from '@heroicons/react/24/outline'
import Button from '../ui/Button'

/**
 * Auto-growing message input. Enter sends, Shift+Enter inserts a newline.
 * `onSend` receives the trimmed text; the field only clears when it returns
 * a value that isn't `false` (the socket helpers report failed sends).
 */
export default function MessageComposer({
  onSend,
  disabled = false,
  sending = false,
  placeholder = 'Type a message…',
}) {
  const [value, setValue] = useState('')
  const taRef = useRef(null)

  const grow = (el) => {
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }

  const reset = () => {
    setValue('')
    if (taRef.current) taRef.current.style.height = 'auto'
  }

  const submit = (e) => {
    e?.preventDefault()
    const text = value.trim()
    if (!text || disabled || sending) return
    if (onSend(text) !== false) reset()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form
      onSubmit={submit}
      className="border-t border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-900"
    >
      <div className="flex items-end gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-1.5 transition focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-800">
        <textarea
          ref={taRef}
          rows={1}
          value={value}
          onChange={(e) => {
            setValue(e.target.value)
            grow(e.target)
          }}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          aria-label="Message"
          className="max-h-36 flex-1 resize-none bg-transparent py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60 dark:text-gray-100"
        />
        <Button
          type="submit"
          size="icon"
          className="mb-1 h-9 w-9 shrink-0"
          loading={sending}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          {!sending && <PaperAirplaneIcon className="h-5 w-5" />}
        </Button>
      </div>
    </form>
  )
}
