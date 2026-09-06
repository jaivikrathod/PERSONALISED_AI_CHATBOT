import { useState } from 'react'
import { ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline'
import { Button, Input } from '../../components/ui'

/**
 * Optional "who are you" step shown once per browser before the first message.
 * Nothing here is required — the backend accepts anonymous messages — but a
 * name and email make the conversation far more useful to the human agent who
 * may end up taking it over, so we ask before we start.
 */
export default function PreChatForm({ companyName, onStart }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [emailError, setEmailError] = useState('')

  const submit = (e) => {
    e.preventDefault()
    const trimmedEmail = email.trim()
    if (trimmedEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setEmailError('Enter a valid email address.')
      return
    }
    onStart({ name: name.trim(), email: trimmedEmail })
  }

  return (
    <div className="flex h-full items-center justify-center px-4 py-10">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900"
      >
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 text-white">
          <ChatBubbleLeftRightIcon className="h-6 w-6" />
        </span>

        <h1 className="mt-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Chat with {companyName || 'support'}
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Ask anything. If we can&rsquo;t answer it automatically, a support agent
          will pick up the conversation.
        </p>

        <div className="mt-5 space-y-3">
          <Input
            name="name"
            label="Your name (optional)"
            placeholder="Jane Doe"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
          />
          <Input
            name="email"
            type="email"
            label="Email (optional)"
            placeholder="jane@example.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              setEmailError('')
            }}
            error={emailError}
            autoComplete="email"
          />
        </div>

        <Button type="submit" className="mt-5 w-full">
          Start chatting
        </Button>
        <p className="mt-3 text-center text-xs text-gray-400 dark:text-gray-500">
          You can leave both fields blank and chat anonymously.
        </p>
      </form>
    </div>
  )
}
