import { useRef, useState } from 'react'
import { PaperAirplaneIcon, PaperClipIcon, FaceSmileIcon } from '@heroicons/react/24/outline'
import Button from '../ui/Button'

/**
 * Auto-growing message input. Enter sends, Shift+Enter newlines.
 * Calls onTyping(true/false) so a typing indicator can be broadcast.
 */
export default function MessageComposer({ onSend, onTyping, disabled, sending }) {
  const [value, setValue] = useState('')
  const typingRef = useRef(false)
  const timeoutRef = useRef(null)
  const taRef = useRef(null)

  const grow = (el) => {
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }

  const handleChange = (e) => {
    setValue(e.target.value)
    grow(e.target)
    if (!typingRef.current) {
      typingRef.current = true
      onTyping?.(true)
    }
    clearTimeout(timeoutRef.current)
    timeoutRef.current = setTimeout(() => {
      typingRef.current = false
      onTyping?.(false)
    }, 1200)
  }

  const submit = () => {
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue('')
    if (taRef.current) taRef.current.style.height = 'auto'
    typingRef.current = false
    onTyping?.(false)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-900">
      <div className="flex items-end gap-2 rounded-xl border border-gray-200 bg-gray-50 px-2 py-1.5 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-800">
        <button className="rounded-lg p-2 text-gray-400 transition hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-700">
          <PaperClipIcon className="h-5 w-5" />
        </button>
        <textarea
          ref={taRef}
          rows={1}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKey}
          disabled={disabled}
          placeholder="Type a message…"
          className="max-h-36 flex-1 resize-none bg-transparent py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none dark:text-gray-100"
        />
        <button className="rounded-lg p-2 text-gray-400 transition hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-700">
          <FaceSmileIcon className="h-5 w-5" />
        </button>
        <Button size="icon" onClick={submit} loading={sending} disabled={disabled || !value.trim()}>
          <PaperAirplaneIcon className="h-5 w-5" />
        </Button>
      </div>
    </div>
  )
}
